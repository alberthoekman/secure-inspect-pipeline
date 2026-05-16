"""API tests for inspection pipeline."""

import pytest


def test_health_check(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_info_endpoint(client):
    """Test info endpoint."""
    response = client.get("/info")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "validation" in data
    assert data["validation"]["min_width"] == 64
    assert data["validation"]["min_height"] == 64


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "endpoints" in response.json()


def test_inspect_valid_image(valid_image, client):
    """Test inspection with valid image."""
    response = client.post(
        "/inspect", files={"file": ("test.png", valid_image, "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "request_id" in data
    assert "detections" in data
    assert "metrics" in data
    assert "inference_time_ms" in data["metrics"]


def test_inspect_small_image(small_image, client):
    """Test rejection of too-small image."""
    response = client.post(
        "/inspect", files={"file": ("small.png", small_image, "image/png")}
    )
    assert response.status_code == 400
    assert "Validation failed" in response.json()["detail"]


def test_inspect_empty_file(client):
    """Test rejection of empty file."""
    response = client.post("/inspect", files={"file": ("empty.png", b"", "image/png")})
    assert response.status_code == 400


def test_inspect_invalid_format(client):
    """Test rejection of invalid file format."""
    response = client.post(
        "/inspect", files={"file": ("test.txt", b"not an image", "text/plain")}
    )
    assert response.status_code == 400


def test_batch_inspect_no_files(client):
    """Test batch endpoint without files."""
    response = client.post("/batch", files=[])
    assert response.status_code == 400


def test_batch_inspect_too_many_files(valid_image, client):
    """Test batch endpoint with >10 files."""
    files = [("test.png", valid_image, "image/png")] * 11
    response = client.post("/batch", files=files)
    assert response.status_code == 400


def test_batch_inspect_valid(valid_image, client):
    """Test batch inspection with valid images."""
    files = [
        ("test1.png", valid_image, "image/png"),
        ("test2.png", valid_image, "image/png"),
    ]
    response = client.post("/batch", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["total_files"] == 2
    assert data["successful"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
