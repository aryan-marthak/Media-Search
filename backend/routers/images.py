from typing import Annotated, List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User, Image
from auth import get_current_user
from services.storage import save_image, delete_image_files
from workers.processor import process_image_task

router = APIRouter()


class ImageResponse(BaseModel):
    id: UUID
    filename: str
    original_filename: str
    file_path: str
    thumbnail_path: Optional[str]
    processing_status: str
    created_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ImageListResponse(BaseModel):
    images: List[ImageResponse]
    total: int


@router.post("/upload", response_model=List[ImageResponse], status_code=status.HTTP_201_CREATED)
async def upload_images(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload one or more images. Processing happens in background."""
    uploaded_images = []
    
    for file in files:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            continue
        
        # Save file and create DB record
        image = await save_image(file, current_user.id, db)
        uploaded_images.append(image)
        
        # Queue background processing
        background_tasks.add_task(process_image_task, str(image.id))
    
    if not uploaded_images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid images uploaded"
        )
    
    return uploaded_images


@router.get("/", response_model=ImageListResponse)
async def list_images(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """List all images owned by the current user."""
    # Get total count
    count_result = await db.execute(
        select(Image).where(Image.owner_id == current_user.id)
    )
    total = len(count_result.scalars().all())
    
    # Get paginated results
    result = await db.execute(
        select(Image)
        .where(Image.owner_id == current_user.id)
        .order_by(Image.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    images = result.scalars().all()
    
    return ImageListResponse(images=images, total=total)


@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific image by ID."""
    result = await db.execute(
        select(Image).where(Image.id == image_id, Image.owner_id == current_user.id)
    )
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    return image


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an image and all related data (faces, embeddings)."""
    from models import Face
    from services.qdrant import delete_image_embedding, delete_face_embedding
    
    result = await db.execute(
        select(Image).where(Image.id == image_id, Image.owner_id == current_user.id)
    )
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Delete related faces first (to satisfy foreign key constraint)
    faces_result = await db.execute(
        select(Face).where(Face.image_id == image_id)
    )
    faces = faces_result.scalars().all()
    
    for face in faces:
        # Delete face embedding from Qdrant
        try:
            await delete_face_embedding(str(current_user.id), str(face.id))
        except Exception:
            pass  # Ignore Qdrant errors
        await db.delete(face)
    
    # Delete image embedding from Qdrant
    try:
        await delete_image_embedding(str(current_user.id), str(image_id))
    except Exception:
        pass  # Ignore Qdrant errors
    
    # Delete files from storage
    await delete_image_files(image)
    
    # Delete image from database
    await db.delete(image)
    await db.commit()


@router.get("/{image_id}/status")
async def get_processing_status(
    image_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get processing status for an image."""
    result = await db.execute(
        select(Image).where(Image.id == image_id, Image.owner_id == current_user.id)
    )
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    return {
        "id": image.id,
        "status": image.processing_status,
        "error": image.processing_error,
        "processed_at": image.processed_at
    }
