"""Image storage adapter.

Local development: files go to static/uploads/.
Production: if CLOUDINARY_URL is configured, images are uploaded to Cloudinary.
"""
import os
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
LOCAL_UPLOAD_DIR = BASE_DIR / "static" / "uploads"
LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_uploaded_image(file, allowed_extensions):
    if not file or not file.filename:
        return ""
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        return ""

    public_id = f"campus_find/{uuid.uuid4().hex}"
    cloudinary_url = os.getenv("CLOUDINARY_URL", "").strip()

    if cloudinary_url:
        try:
            import cloudinary
            import cloudinary.uploader
            cloudinary.config(cloudinary_url=cloudinary_url)
            result = cloudinary.uploader.upload(
                file,
                folder="campus_find",
                public_id=public_id.split("/", 1)[1],
                resource_type="image",
            )
            return result["secure_url"]
        except Exception as exc:
            raise RuntimeError(f"Cloud image upload failed: {exc}") from exc

    filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
    target = LOCAL_UPLOAD_DIR / filename
    file.save(target)
    return f"/static/uploads/{filename}"
