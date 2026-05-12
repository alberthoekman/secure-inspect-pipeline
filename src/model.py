"""YOLOv8 object detection model inference."""

import time
from typing import List, Dict, Any, Optional

from PIL import Image
from ultralytics import YOLO

from .monitoring import InferenceMetrics


class ObjectDetectionModel:
    """Wrapper for YOLOv8 inference."""

    def __init__(
        self, model_name: str = "yolov8n.pt", confidence_threshold: float = 0.5
    ):
        """
        Initialize YOLOv8 model.

        Args:
            model_name: Model weights file (default: nano model)
            confidence_threshold: Min confidence for detections
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.model: Optional[YOLO] = None
        self._load_model()

    def _load_model(self):
        """Load YOLOv8 model from Ultralytics."""
        try:
            self.model = YOLO(self.model_name)
            # Set to eval mode
            self.model.eval()
        except Exception as e:
            raise RuntimeError(f"Failed to load model {self.model_name}: {str(e)}")

    def predict(
        self, image: Image.Image, metrics: InferenceMetrics
    ) -> List[Dict[str, Any]]:
        """
        Run inference on image.

        Args:
            image: PIL Image
            metrics: InferenceMetrics object to record timing

        Returns:
            List of detections with class, confidence, box coords
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")

        # Ensure image is in RGB mode
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Run inference
        start_inference = time.time()
        try:
            results = self.model(image, conf=self.confidence_threshold, verbose=False)
            inference_time_ms = (time.time() - start_inference) * 1000

            # Parse results
            detections = self._parse_results(results)
            metrics.record_inference(inference_time_ms, detections)

            return detections

        except Exception as e:
            metrics.record_error(str(e))
            raise RuntimeError(f"Inference failed: {str(e)}")

    def _parse_results(self, results) -> List[Dict[str, Any]]:
        """
        Parse YOLOv8 results into standard format.

        Args:
            results: YOLO prediction results

        Returns:
            List of detection dicts
        """
        detections = []

        if not results or len(results) == 0:
            return detections

        # Get first (and usually only) result
        result = results[0]

        if result.boxes is None or len(result.boxes) == 0:
            return detections

        # Iterate detections
        boxes = result.boxes.cpu().numpy()
        names = result.names

        for box in boxes:
            detection = {
                "class_id": int(box.cls[0]) if len(box.cls) > 0 else -1,
                "class_name": names.get(int(box.cls[0])) if names else "unknown",
                "confidence": float(box.conf[0]) if len(box.conf) > 0 else 0.0,
                "box": {
                    "x_min": float(box.xyxy[0][0]),
                    "y_min": float(box.xyxy[0][1]),
                    "x_max": float(box.xyxy[0][2]),
                    "y_max": float(box.xyxy[0][3]),
                },
                "box_area": float(
                    (box.xyxy[0][2] - box.xyxy[0][0])
                    * (box.xyxy[0][3] - box.xyxy[0][1])
                ),
            }
            detections.append(detection)

        # Sort by confidence descending
        detections.sort(key=lambda x: x["confidence"], reverse=True)

        return detections

    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata."""
        return {
            "model_name": self.model_name,
            "framework": "ultralytics/YOLOv8",
            "confidence_threshold": self.confidence_threshold,
            "task": "object-detection",
        }
