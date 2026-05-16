"""Unit tests for monitoring module — InferenceMetrics."""

import time
from src.monitoring import (
    InferenceMetrics,
    log_inference_metrics,
    log_validation_error,
    log_api_request,
)


class TestInferenceMetrics:
    """Metrics tracking tests."""

    def test_initial_state(self):
        """Metrics start in pending state with no results."""
        metrics = InferenceMetrics("req-001")

        assert metrics.request_id == "req-001"
        assert metrics.status == "pending"
        assert metrics.inference_time_ms is None
        assert metrics.num_detections == 0
        assert metrics.confidence_scores == []
        assert metrics.error is None

    def test_record_inference_sets_success(self):
        """record_inference updates state correctly."""
        metrics = InferenceMetrics("req-002")
        detections = [
            {"confidence": 0.95},
            {"confidence": 0.85},
            {"confidence": 0.75},
        ]

        metrics.record_inference(42.5, detections)

        assert metrics.status == "success"
        assert metrics.inference_time_ms == 42.5
        assert metrics.num_detections == 3
        assert metrics.confidence_scores == [0.95, 0.85, 0.75]

    def test_record_inference_no_detections(self):
        """record_inference with empty detections."""
        metrics = InferenceMetrics("req-003")

        metrics.record_inference(10.0, [])

        assert metrics.status == "success"
        assert metrics.num_detections == 0
        assert metrics.confidence_scores == []

    def test_record_error_sets_error_state(self):
        """record_error sets error status and message."""
        metrics = InferenceMetrics("req-004")

        metrics.record_error("Model crashed")

        assert metrics.status == "error"
        assert metrics.error == "Model crashed"

    def test_get_metrics_returns_correct_shape(self):
        """get_metrics returns all expected fields."""
        metrics = InferenceMetrics("req-005")
        metrics.record_inference(35.2, [{"confidence": 0.90}])

        result = metrics.get_metrics()

        assert result["request_id"] == "req-005"
        assert result["status"] == "success"
        assert result["inference_time_ms"] == 35.2
        assert result["detections_count"] == 1
        assert result["avg_confidence"] == 0.9
        assert result["confidence_scores"] == [0.9]
        assert result["error"] is None
        assert "timestamp" in result
        assert "model" in result
        assert result["model"] == "YOLOv8n"
        assert "total_request_time_ms" in result
        assert isinstance(result["total_request_time_ms"], (int, float))

    def test_get_metrics_with_error(self):
        """get_metrics after error reflects the failure."""
        metrics = InferenceMetrics("req-006")
        metrics.record_error("Timeout")

        result = metrics.get_metrics()

        assert result["status"] == "error"
        assert result["error"] == "Timeout"
        assert result["inference_time_ms"] is None
        assert result["detections_count"] == 0
        assert result["avg_confidence"] == 0.0
        assert result["confidence_scores"] == []

    def test_get_metrics_total_time_increases(self):
        """total_request_time_ms reflects elapsed time."""
        metrics = InferenceMetrics("req-007")
        time.sleep(0.01)  # ~10 ms

        result = metrics.get_metrics()

        assert result["total_request_time_ms"] > 0
        assert result["total_request_time_ms"] < 5000  # sanity bound

    def test_avg_confidence_with_empty_scores(self):
        """Empty confidence scores produce zero avg."""
        metrics = InferenceMetrics("req-008")

        result = metrics.get_metrics()

        assert result["avg_confidence"] == 0.0

    def test_logging_functions_exist(self):
        """Logging functions can be called without error."""
        # These are smoke checks — structlog writes to stderr by default,
        # so we just verify they don't raise.
        log_validation_error("req-009", "invalid format")
        log_inference_metrics(
            {
                "request_id": "req-010",
                "model": "YOLOv8n",
                "inference_time_ms": 30.0,
                "detections_count": 2,
                "avg_confidence": 0.85,
                "status": "success",
            }
        )
        log_api_request("POST", "/inspect", 200, 150.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
