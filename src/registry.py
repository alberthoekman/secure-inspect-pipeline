"""MLflow model registry and tracking."""

import os
import json
import logging
from typing import Dict, Optional

import mlflow

logger = logging.getLogger(__name__)


class MLflowRegistry:
    """MLflow model tracking and registry."""

    def __init__(
        self,
        tracking_uri: str = "http://localhost:5000",
        experiment_name: str = "secure-inspect",
    ):
        """Initialize MLflow registry."""
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)

    def log_training_run(
        self,
        model_path: str,
        metrics: Dict[str, float],
        params: Dict[str, any],
        model_name: str = "yolov8-inspect",
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """Log training run to MLflow."""
        with mlflow.start_run():
            for key, value in params.items():
                mlflow.log_param(key, value)

            for key, value in metrics.items():
                mlflow.log_metric(key, value)

            if tags:
                for key, value in tags.items():
                    mlflow.set_tag(key, value)

            mlflow.log_artifact(model_path, artifact_path="models")

            run_id = mlflow.active_run().info.run_id
            logger.info(f"Logged run {run_id} to MLflow")
            return run_id

    def register_model(
        self, model_uri: str, model_name: str = "yolov8-inspect", stage: str = "Staging"
    ) -> str:
        """Register model in MLflow registry."""
        try:
            result = mlflow.register_model(model_uri, model_name)
            logger.info(f"Registered model {model_name} version {result.version}")

            client = mlflow.tracking.MlflowClient()
            client.transition_model_version_stage(
                name=model_name, version=result.version, stage=stage
            )
            logger.info(f"Transitioned {model_name}@{result.version} to {stage}")
            return result.version
        except Exception as e:
            logger.error(f"Failed to register model: {str(e)}")
            raise

    def get_model_version(
        self, model_name: str = "yolov8-inspect", stage: str = "Production"
    ) -> Optional[Dict]:
        """Get model version from registry."""
        try:
            client = mlflow.tracking.MlflowClient()
            versions = client.get_latest_versions(model_name, stages=[stage])
            if versions:
                return {
                    "version": versions[0].version,
                    "stage": versions[0].current_stage,
                    "status": versions[0].status,
                }
            return None
        except Exception as e:
            logger.warning(f"Model not found in {stage}: {str(e)}")
            return None

    def get_best_run(self, metric_name: str = "mAP") -> Optional[Dict]:
        """Get best run by metric."""
        try:
            experiment = mlflow.get_experiment_by_name(self.experiment_name)
            if not experiment:
                return None

            runs = mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=[f"metrics.{metric_name} DESC"],
                max_results=1,
            )

            if runs.empty:
                return None

            run = runs.iloc[0]
            return {
                "run_id": run.run_id,
                "metrics": dict(run.filter_regex(r"^metrics\.")),
                "params": dict(run.filter_regex(r"^params\.")),
            }
        except Exception as e:
            logger.error(f"Failed to get best run: {str(e)}")
            return None


def load_baseline_metrics(
    baseline_path: str = "baseline_metrics.json",
) -> Dict[str, float]:
    """Load baseline metrics for comparison."""
    if os.path.exists(baseline_path):
        with open(baseline_path, "r") as f:
            return json.load(f)
    return {"mAP": 0.0, "precision": 0.0, "recall": 0.0}


def save_baseline_metrics(
    metrics: Dict[str, float], baseline_path: str = "baseline_metrics.json"
):
    """Save baseline metrics for future comparisons."""
    with open(baseline_path, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Saved baseline metrics to {baseline_path}")
