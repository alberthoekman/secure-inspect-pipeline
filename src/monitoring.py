"""Performance monitoring and logging."""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

import structlog


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class InferenceMetrics:
    """Track inference metrics for a single request."""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self.start_time = time.time()
        self.inference_time_ms: Optional[float] = None
        self.confidence_scores: list = []
        self.num_detections: int = 0
        self.model_name: str = "YOLOv8n"
        self.status: str = "pending"
        self.error: Optional[str] = None

    def record_inference(self, inference_time_ms: float, detections: list):
        """Record inference results."""
        self.inference_time_ms = inference_time_ms
        self.num_detections = len(detections)
        self.confidence_scores = [d.get("confidence", 0.0) for d in detections]
        self.status = "success"

    def record_error(self, error_msg: str):
        """Record error state."""
        self.status = "error"
        self.error = error_msg

    def get_metrics(self) -> Dict[str, Any]:
        """Return metrics dict."""
        total_time_ms = (time.time() - self.start_time) * 1000
        avg_confidence = (
            sum(self.confidence_scores) / len(self.confidence_scores)
            if self.confidence_scores
            else 0.0
        )

        return {
            "request_id": self.request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "model": self.model_name,
            "status": self.status,
            "inference_time_ms": self.inference_time_ms,
            "total_request_time_ms": round(total_time_ms, 2),
            "detections_count": self.num_detections,
            "avg_confidence": round(avg_confidence, 4),
            "confidence_scores": [round(c, 4) for c in self.confidence_scores],
            "error": self.error,
        }


def log_inference_metrics(metrics: Dict[str, Any]):
    """Log inference metrics to structured logger."""
    logger.info(
        "inference_complete",
        request_id=metrics["request_id"],
        model=metrics["model"],
        inference_time_ms=metrics["inference_time_ms"],
        detections=metrics["detections_count"],
        avg_confidence=metrics["avg_confidence"],
        status=metrics["status"],
    )


def log_validation_error(request_id: str, error: str):
    """Log validation error."""
    logger.warning(
        "validation_failed",
        request_id=request_id,
        error=error,
    )


def log_api_request(method: str, path: str, status_code: int, duration_ms: float):
    """Log API request."""
    logger.info(
        "api_request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration_ms, 2),
    )
