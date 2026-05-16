"""Unit tests for validation module."""

import pytest

from src.validation import ValidationError, validate_image_file


class TestValidation:
    """Unit tests for validation module."""

    def test_validate_image_valid(self, valid_image):
        """Test validation with valid image."""
        image, metadata = validate_image_file(valid_image)
        assert metadata.is_valid
        assert metadata.width == 640
        assert metadata.height == 480
        assert metadata.format in ["PNG", "JPEG", "JPG", "BMP", "TIFF"]

    def test_validate_image_too_small(self, small_image):
        """Test validation with small image."""
        with pytest.raises(ValidationError):
            validate_image_file(small_image)

    def test_validate_empty_file(self):
        """Test validation with empty file."""
        with pytest.raises(ValidationError):
            validate_image_file(b"")

    def test_validate_invalid_file(self):
        """Test validation with invalid file."""
        with pytest.raises(ValidationError):
            validate_image_file(b"not an image")

    def test_validate_too_large(self):
        """Test validation with oversized file."""
        # Create large byte sequence
        large_bytes = b"x" * (11 * 1024 * 1024)  # 11 MB
        with pytest.raises(ValidationError):
            validate_image_file(large_bytes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
