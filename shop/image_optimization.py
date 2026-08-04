"""Helpers to keep catalogue images small without sacrificing display quality."""

from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_IMAGE_DIMENSION = getattr(settings, "PRODUCT_IMAGE_MAX_DIMENSION", 1600)
WEBP_QUALITY = getattr(settings, "PRODUCT_IMAGE_WEBP_QUALITY", 82)


def optimize_product_image(image_field):
    """Convert a catalogue image to resized WebP and return whether it changed.

    Images that are already WebP (or unsupported by Pillow, such as some AVIF
    files) are deliberately left untouched.
    """
    if not image_field or not image_field.name:
        return False

    source_name = image_field.name
    if Path(source_name).suffix.lower() in {".webp", ".avif"}:
        return False

    try:
        image_field.open("rb")
        with Image.open(image_field) as opened_image:
            image = ImageOps.exif_transpose(opened_image)
            image.thumbnail(
                (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS
            )
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")

            output = BytesIO()
            image.save(output, format="WEBP", quality=WEBP_QUALITY, method=6)
    except (OSError, UnidentifiedImageError):
        return False
    finally:
        image_field.close()

    # FieldFile.save() applies the field's upload_to path itself, so pass only
    # the filename here (not the original directory).
    optimized_name = f"{Path(source_name).stem}.webp"
    image_field.save(optimized_name, ContentFile(output.getvalue()), save=False)
    if source_name != image_field.name:
        image_field.storage.delete(source_name)
    return True
