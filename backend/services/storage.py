import os
import aiofiles
from uuid import uuid4, UUID
from pathlib import Path
from PIL import Image as PILImage
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from config import IMAGES_DIR, THUMBNAILS_DIR, THUMBNAIL_SIZE, ALLOWED_EXTENSIONS
from models import Image


async def save_image(file: UploadFile, user_id: UUID, db: AsyncSession) -> Image:
    """Save uploaded image to filesystem and create database record."""
    # Create user directory
    user_images_dir = IMAGES_DIR / str(user_id)
    user_thumbs_dir = THUMBNAILS_DIR / str(user_id)
    user_images_dir.mkdir(parents=True, exist_ok=True)
    user_thumbs_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    original_filename = file.filename or "unknown"
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".jpg"
    
    image_id = uuid4()
    filename = f"{image_id}{ext}"
    file_path = user_images_dir / filename
    thumb_filename = f"{image_id}_thumb.webp"
    thumb_path = user_thumbs_dir / thumb_filename
    
    # Save original file
    content = await file.read()
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)
    
    # Create thumbnail
    try:
        with PILImage.open(file_path) as img:
            img.thumbnail(THUMBNAIL_SIZE)
            # Convert to RGB if necessary (for RGBA images)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(thumb_path, "WEBP", quality=80)
            width, height = img.size
    except Exception:
        width, height = 0, 0
    
    # Create database record
    image = Image(
        id=image_id,
        owner_id=user_id,
        filename=filename,
        original_filename=original_filename,
        file_path=str(file_path.relative_to(IMAGES_DIR.parent)),
        thumbnail_path=str(thumb_path.relative_to(THUMBNAILS_DIR.parent)),
        file_size=str(len(content)),
        mime_type=file.content_type,
        width=str(width),
        height=str(height),
        processing_status="pending"
    )
    
    db.add(image)
    await db.commit()
    await db.refresh(image)
    
    return image


async def delete_image_files(image: Image) -> None:
    """Delete image and thumbnail files from filesystem."""
    base_dir = IMAGES_DIR.parent
    
    # Delete original
    file_path = base_dir / image.file_path
    if file_path.exists():
        os.remove(file_path)
    
    # Delete thumbnail
    if image.thumbnail_path:
        thumb_path = base_dir / image.thumbnail_path
        if thumb_path.exists():
            os.remove(thumb_path)


def get_image_path(image: Image) -> Path:
    """Get full path to image file."""
    return IMAGES_DIR.parent / image.file_path
