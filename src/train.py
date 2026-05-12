"""Model training and fine-tuning."""

import os
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional
from datetime import datetime

import torch
from ultralytics import YOLO
import mlflow
import mlflow.pytorch

logger = logging.getLogger(__name__)


class ModelTrainer:
    """YOLOv8 model trainer for continuous training."""

    def __init__(self, base_model: str = "yolov8n.pt", device: str = "cpu"):
        """Initialize trainer."""
        self.base_model = base_model
        self.device = device
        self.model = None

    def load_model(self) -> YOLO:
        """Load base model."""
        try:
            self.model = YOLO(self.base_model)
            self.model.to(self.device)
            logger.info(f"Loaded model {self.base_model} on {self.device}")
            return self.model
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise

    def train(
        self,
        data_yaml: str,
        epochs: int = 10,
        imgsz: int = 640,
        batch_size: int = 8,
        lr0: float = 0.001,
        patience: int = 5,
        save_dir: str = "runs/detect",
    ) -> Dict[str, float]:
        """Fine-tune model on new data."""
        if not self.model:
            self.load_model()

        try:
            logger.info(f"Starting training for {epochs} epochs")

            results = self.model.train(
                data=data_yaml,
                epochs=epochs,
                imgsz=imgsz,
                batch=batch_size,
                lr0=lr0,
                patience=patience,
                device=self.device,
                project=save_dir,
                name=f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                verbose=True,
                save=True,
                exist_ok=False,
            )

            metrics = self._extract_metrics(results)
            logger.info(f"Training complete. Metrics: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"Training failed: {str(e)}")
            raise

    def _extract_metrics(self, results) -> Dict[str, float]:
        """Extract key metrics from training results."""
        try:
            return {
                "mAP": float(results.results_dict.get("metrics/mAP50", 0.0)),
                "mAP50_95": float(results.results_dict.get("metrics/mAP50-95", 0.0)),
                "precision": float(results.results_dict.get("metrics/precision", 0.0)),
                "recall": float(results.results_dict.get("metrics/recall", 0.0)),
                "loss": float(results.results_dict.get("train/loss", 0.0)),
            }
        except Exception as e:
            logger.warning(f"Failed to extract metrics: {str(e)}")
            return {}

    def export_model(self, export_dir: str = "models") -> str:
        """Export trained model."""
        if not self.model:
            raise RuntimeError("Model not loaded")

        try:
            os.makedirs(export_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_path = os.path.join(export_dir, f"yolov8n_{timestamp}.pt")

            self.model.save(model_path)
            logger.info(f"Exported model to {model_path}")
            return model_path

        except Exception as e:
            logger.error(f"Failed to export model: {str(e)}")
            raise


def train_with_mlflow(
    data_yaml: str,
    epochs: int = 10,
    batch_size: int = 8,
    lr0: float = 0.001,
    device: str = "cpu",
    experiment_name: str = "secure-inspect",
    run_name: Optional[str] = None,
) -> Tuple[Dict[str, float], str]:
    """Train model and log to MLflow."""
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(
        run_name=run_name or f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    ):
        mlflow.log_param("base_model", "yolov8n.pt")
        mlflow.log_param("epochs", epochs)
        mlflow.log_param("batch_size", batch_size)
        mlflow.log_param("learning_rate", lr0)
        mlflow.log_param("device", device)

        trainer = ModelTrainer(device=device)
        trainer.load_model()

        try:
            metrics = trainer.train(
                data_yaml=data_yaml, epochs=epochs, batch_size=batch_size, lr0=lr0
            )

            for key, value in metrics.items():
                mlflow.log_metric(key, value)

            model_path = trainer.export_model()
            mlflow.log_artifact(model_path, artifact_path="models")

            mlflow.set_tag("status", "success")
            mlflow.set_tag("model_path", model_path)

            logger.info(
                f"Training run complete. Run ID: {mlflow.active_run().info.run_id}"
            )
            return metrics, model_path

        except Exception as e:
            mlflow.set_tag("status", "failed")
            logger.error(f"Training run failed: {str(e)}")
            raise
