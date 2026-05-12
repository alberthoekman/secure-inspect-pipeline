"""Shared test fixtures."""

import io
import pytest
from PIL import Image


@pytest.fixture
def valid_image():
    """Create valid test image."""
    img = Image.new("RGB", (640, 480), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


@pytest.fixture
def small_image():
    """Create too-small test image."""
    img = Image.new("RGB", (32, 32), color="blue")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()
