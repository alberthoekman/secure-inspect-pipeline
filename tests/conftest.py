"""Shared test fixtures."""

import io
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image


@pytest.fixture(scope="module")
def client():
    """Create a FastAPI test client with YOLO mocked to avoid model downloads.

    The patches are active before TestClient construction so the startup
    event (which loads ObjectDetectionModel) never hits the real YOLO.
    """
    with patch("ultralytics.YOLO") as mock_yolo_cls:
        mock_yolo_instance = MagicMock()
        mock_yolo_instance.eval.return_value = None
        mock_yolo_cls.return_value = mock_yolo_instance

        # Import inside patch context — ObjectDetectionModel.__init__
        # calls YOLO() during startup event, which resolves to the mock.
        from fastapi.testclient import TestClient
        from src.app import app

        with patch("src.model.ObjectDetectionModel.predict") as mock_predict:
            mock_predict.return_value = [
                {
                    "class_id": 0,
                    "class_name": "person",
                    "confidence": 0.95,
                    "box": {
                        "x_min": 100.0,
                        "y_min": 200.0,
                        "x_max": 300.0,
                        "y_max": 400.0,
                    },
                    "box_area": 20000.0,
                }
            ]
            yield TestClient(app)


@pytest.fixture
def valid_image():
    """Create valid test image (640x480)."""
    img = Image.new("RGB", (640, 480), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


@pytest.fixture
def small_image():
    """Create too-small test image (32x32)."""
    img = Image.new("RGB", (32, 32), color="blue")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()
