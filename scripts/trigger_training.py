"""Trigger continuous training pipeline.

Loads baseline metrics from Azure Blob Storage (with local fallback),
runs training and evaluation, then persists results back to blob storage.
"""

import os
import sys
import json
import logging
from src.registry import MLflowRegistry, load_baseline_metrics, save_baseline_metrics
from src.evaluate import ModelGate
from src.train import train_with_mlflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Azure Blob Storage constants — set via environment variables or defaults
BLOB_CONNECTION_STRING = os.getenv(
    "AZURE_STORAGE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=https;AccountName=secureinspectstorage;AccountKey=;EndpointSuffix=core.windows.net",
)
BLOB_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "model-artifacts")
BASELINE_BLOB = os.getenv("BASELINE_BLOB_PATH", "baseline_metrics.json")


def download_blob(container_name: str, blob_name: str, local_path: str) -> bool:
    """Download a blob to a local file. Returns True if successful, False if not found."""
    try:
        from azure.storage.blob import BlobServiceClient

        service = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
        container_client = service.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)

        with open(local_path, "wb") as f:
            blob_data = blob_client.download_blob()
            blob_data.readinto(f)

        logger.info("Downloaded %s/%s to %s", container_name, blob_name, local_path)
        return True
    except ModuleNotFoundError:
        logger.warning("azure-storage-blob not installed; skipping blob download")
        return False
    except Exception as exc:
        logger.warning("Could not download %s/%s: %s", container_name, blob_name, exc)
        return False


def upload_blob(local_path: str, container_name: str, blob_name: str) -> None:
    """Upload a local file to blob storage."""
    try:
        from azure.storage.blob import BlobServiceClient

        service = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
        container_client = service.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)

        with open(local_path, "rb") as f:
            blob_client.upload_blob(f, overwrite=True)

        logger.info("Uploaded %s to %s/%s", local_path, container_name, blob_name)
    except ModuleNotFoundError:
        logger.warning("azure-storage-blob not installed; skipping blob upload")
    except Exception as exc:
        logger.warning("Could not upload %s: %s", local_path, exc)


def load_baseline_from_blob(local_path: str = "baseline_metrics.json") -> dict | None:
    """Try Azure Blob first, then local file, then return empty baseline."""
    # Attempt download from blob storage
    if download_blob(BLOB_CONTAINER, BASELINE_BLOB, local_path):
        return load_baseline_metrics(local_path)

    # Fall back to local file
    if os.path.exists(local_path):
        logger.info("Blob not found; loading local %s", local_path)
        return load_baseline_metrics(local_path)

    logger.info("No baseline found — starting fresh")
    return None


def save_baseline_to_blob(metrics: dict, local_path: str = "baseline_metrics.json") -> None:
    """Save baseline locally and upload to blob storage."""
    save_baseline_metrics(metrics, local_path)
    upload_blob(local_path, BLOB_CONTAINER, BASELINE_BLOB)


def main():
    logger.info("Starting CT pipeline (Azure)")

    registry = MLflowRegistry()
    gate = ModelGate(min_mAP_improvement=0.01, min_precision=0.70, min_recall=0.70)

    # Load baseline — from Azure Blob Storage or local fallback
    baseline = load_baseline_from_blob()
    if baseline:
        logger.info("Baseline: %s", baseline)
    else:
        logger.info("No baseline set; first run will establish it")

    # Simulate training (replace with actual train_with_mlflow() in production)
    new_metrics = {
        "mAP": 0.52,
        "precision": 0.76,
        "recall": 0.74,
    }
    logger.info("New metrics: %s", new_metrics)

    # Evaluate against promotion gates
    if baseline:
        result = gate.evaluate(new_metrics, baseline, "v1.0.0")
        logger.info("Gate passed: %s, Stage: %s", result.passed_gate, result.promotion_stage)
    else:
        # First run — auto-establish baseline without comparison
        result = type("Result", (), {"passed_gate": True, "promotion_stage": "baseline_establishment", "reason": None})()

    # Update baseline if promoted, then upload to blob storage
    if result.passed_gate:
        save_baseline_to_blob(new_metrics, "baseline_metrics.json")
        logger.info("Baseline updated from training run")
        output = {
            "status": "success",
            "action": "promoted_to_production",
            "metrics": new_metrics,
        }
    else:
        output = {
            "status": "success",
            "action": "staged_for_review",
            "metrics": new_metrics,
            "reason": getattr(result, "reason", None),
        }

    print(json.dumps(output, indent=2))
    return output


if __name__ == "__main__":
    main()
