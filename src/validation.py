"""Image validation and quality checks."""

import io
from pathlib import Path
from typing import Tuple

from PIL import Image
from pydantic import BaseModel, Field, field_validator


class ImageValidationConfig:
    """Validation thresholds."""
    MIN_WIDTH = 64
    MIN_HEIGHT = 64
    MAX_FILE_SIZE_MB = 10
    ALLOWED_FORMATS = {"PNG", "JPEG", "JPG", "BMP", "TIFF"}


class ImageMetadata(BaseModel):
    """Image metadata after validation."""
    width: int = Field(..., ge=1)
    height: int = Field(..., ge=1)
    format: str
    file_size_bytes: int = Field(..., ge=1)
    is_valid: bool = True

    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v.upper() not in ImageValidationConfig.ALLOWED_FORMATS:
            raise ValueError(f"Format {v} not supported. Allowed: {ImageValidationConfig.ALLOWED_FORMATS}")
        return v.upper()


class ValidationError(Exception):
    """Custom validation exception."""
    pass


def validate_image_file(file_bytes: bytes) -> Tuple[Image.Image, ImageMetadata]:
    """
    Validate image file: format, size, resolution.

    Args:
        file_bytes: Raw image bytes

    Returns:
        Tuple of (PIL Image, ImageMetadata)

    Raises:
        ValidationError: If validation fails
    """
    config = ImageValidationConfig()

    # Check file size
    file_size_bytes = len(file_bytes)
    max_bytes = config.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise ValidationError(
            f"File too large: {file_size_bytes} bytes > {max_bytes} bytes limit"
        )

    if file_size_bytes == 0:
        raise ValidationError("File is empty")

    # Open image
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.load()  # Force load to catch corrupt files
    except Exception as e:
        raise ValidationError(f"Failed to open image: {str(e)}")

    # Validate format
    img_format = image.format or "UNKNOWN"
    if img_format.upper() not in config.ALLOWED_FORMATS:
        raise ValidationError(f"Format not supported: {img_format}")

    # Validate resolution
    width, height = image.size
    if width < config.MIN_WIDTH or height < config.MIN_HEIGHT:
        raise ValidationError(
            f"Image too small: {width}x{height} < {config.MIN_WIDTH}x{config.MIN_HEIGHT} required"
        )

    # Create metadata
    metadata = ImageMetadata(
        width=width,
        height=height,
        format=img_format,
        file_size_bytes=file_size_bytes,
        is_valid=True,
    )

    return image, metadata


def get_validation_summary() -> dict:
    """Get validation config summary."""
    config = ImageValidationConfig()
    return {
        "min_width": config.MIN_WIDTH,
        "min_height": config.MIN_HEIGHT,
        "max_file_size_mb": config.MAX_FILE_SIZE_MB,
        "allowed_formats": list(config.ALLOWED_FORMATS),
    }
