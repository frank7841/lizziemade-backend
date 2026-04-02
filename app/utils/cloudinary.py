import cloudinary
import cloudinary.uploader
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True
)

def upload_image(file_content, folder="products"):
    """
    Uploads an image to Cloudinary.
    """
    try:
        response = cloudinary.uploader.upload(
            file_content,
            folder=f"lizziemade/{folder}",
            resource_type="image"
        )
        return {
            "url": response.get("secure_url"),
            "public_id": response.get("public_id")
        }
    except Exception as e:
        logger.error(f"Cloudinary image upload failed: {e}")
        raise e

def upload_file(file_content, filename, folder="patterns"):
    """
    Uploads a raw file (PDF, etc.) to Cloudinary.
    """
    try:
        response = cloudinary.uploader.upload(
            file_content,
            folder=f"lizziemade/{folder}",
            resource_type="raw",
            public_id=filename,
            use_filename=True,
            unique_filename=True
        )
        return {
            "url": response.get("secure_url"),
            "public_id": response.get("public_id")
        }
    except Exception as e:
        logger.error(f"Cloudinary file upload failed: {e}")
        raise e

def delete_file(public_id, resource_type="image"):
    """
    Deletes a file from Cloudinary.
    """
    try:
        cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        return True
    except Exception as e:
        logger.error(f"Cloudinary delete failed: {e}")
        return False
