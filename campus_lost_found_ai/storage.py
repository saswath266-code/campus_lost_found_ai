"""Safe image storage for local development and optional Cloudinary hosting."""

from __future__ import annotations

import os
import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

BASE_DIR = Path(__file__).resolve().parent
LOCAL_UPLOAD_DIR = BASE_DIR / "static" / "uploads"
LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_FORMATS = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
}


class UploadValidationError(ValueError):
    """Raised when an uploaded object is not a safe supported image."""


def _read_and_validate(file, max_bytes: int) -> tuple[bytes, str]:
    if not file or not getattr(file, "filename", ""):
        return b"", ""

    filename = file.filename
    if "." not in filename or filename.rsplit(".", 1)[1].lower() not in {"jpg", "jpeg", "png", "webp"}:
        raise UploadValidationError("Use a PNG, JPG, JPEG, or WEBP image.")

    stream = file.stream
    stream.seek(0)
    payload = stream.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise UploadValidationError("Image is larger than the allowed upload size.")
    if not payload:
        raise UploadValidationError("The selected image is empty.")

    try:
        with Image.open(BytesIO(payload)) as image:
            image.verify()
        with Image.open(BytesIO(payload)) as image:
            image_format = image.format
            width, height = image.size
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise UploadValidationError("The selected file is not a valid supported image.") from exc

    if image_format not in ALLOWED_FORMATS or width < 1 or height < 1:
        raise UploadValidationError("Use a valid PNG, JPG, JPEG, or WEBP image.")
    return payload, image_format


def save_uploaded_image(file, max_bytes: int) -> str:
    """Validate and store an image, returning only a safe public reference.

    Empty file fields are allowed because a report can still be useful without a
    photo. Any provided file, however, is inspected by Pillow instead of trusted
    based on its name or browser MIME type.
    """

    if not file or not getattr(file, "filename", ""):
        return ""

    payload, image_format = _read_and_validate(file, max_bytes)
    extension, _ = ALLOWED_FORMATS[image_format]
    cloudinary_url = os.getenv("CLOUDINARY_URL", "").strip()

    if cloudinary_url:
        try:
            import cloudinary
            import cloudinary.uploader

            cloudinary.config(cloudinary_url=cloudinary_url)
            result = cloudinary.uploader.upload(
                BytesIO(payload),
                folder="campus_find",
                public_id=uuid.uuid4().hex,
                resource_type="image",
                overwrite=False,
            )
            url = result.get("secure_url", "")
            if not url.startswith("https://"):
                raise RuntimeError("Cloudinary did not return a secure image URL.")
            return url
        except UploadValidationError:
            raise
        except Exception as exc:
            raise RuntimeError("Cloud image upload failed. Please try again.") from exc

    filename = f"{uuid.uuid4().hex}.{extension}"
    target = (LOCAL_UPLOAD_DIR / filename).resolve()
    if target.parent != LOCAL_UPLOAD_DIR.resolve():
        raise UploadValidationError("Unsafe upload path.")
    target.write_bytes(payload)
    return f"/static/uploads/{filename}"
