from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.dependencies import get_current_user
from app.models.user import User
from app.utils.cloudinary import upload_image, upload_file
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["Uploads"])

@router.post(
    "/image",
    summary="Upload Product Image",
    description="Uploads an image file to Cloudinary and returns the secure URL and public ID for storage in the product record."
)
async def upload_product_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads an image to Cloudinary and returns the URL and public_id.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        content = await file.read()
        result = upload_image(content, folder="products")
        return result
    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

@router.post(
    "/pattern",
    summary="Upload Digital Pattern",
    description="Uploads a raw file (e.g., a PDF crochet pattern) to Cloudinary and returns the secure URL."
)
async def upload_pattern_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a raw file (e.g. PDF pattern) to Cloudinary.
    """
    # Only allow PDF or other common pattern formats if needed
    # For now, let's just upload as raw
    
    try:
        content = await file.read()
        result = upload_file(content, file.filename, folder="patterns")
        return result
    except Exception as e:
        logger.error(f"Pattern upload failed: {e}")
        raise HTTPException(status_code=500, detail="Pattern upload failed")
