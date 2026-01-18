from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database import get_db
from models import User, Image, Share, SharePermission
from auth import get_current_user

router = APIRouter()


class ShareRequest(BaseModel):
    image_id: UUID
    shared_with_username: str
    permission: str = "view"  # "view" or "download"


class ShareResponse(BaseModel):
    id: UUID
    image_id: UUID
    shared_with_username: str
    permission: str
    created_at: datetime


class SharedImageResponse(BaseModel):
    id: UUID
    filename: str
    thumbnail_path: Optional[str]
    owner_username: str
    permission: str
    shared_at: datetime


@router.post("/", response_model=ShareResponse, status_code=status.HTTP_201_CREATED)
async def share_image(
    request: ShareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Share an image with another user."""
    # Verify image ownership
    result = await db.execute(
        select(Image).where(Image.id == request.image_id, Image.owner_id == current_user.id)
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Find target user
    result = await db.execute(
        select(User).where(User.username == request.shared_with_username)
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot share with yourself")
    
    # Check if already shared
    result = await db.execute(
        select(Share).where(
            and_(
                Share.image_id == request.image_id,
                Share.shared_with_id == target_user.id
            )
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already shared with this user")
    
    # Create share
    permission = SharePermission.DOWNLOAD if request.permission == "download" else SharePermission.VIEW
    share = Share(
        image_id=request.image_id,
        owner_id=current_user.id,
        shared_with_id=target_user.id,
        permission=permission
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)
    
    return ShareResponse(
        id=share.id,
        image_id=share.image_id,
        shared_with_username=target_user.username,
        permission=request.permission,
        created_at=share.created_at
    )


@router.delete("/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share(
    share_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Revoke a share."""
    result = await db.execute(
        select(Share).where(Share.id == share_id, Share.owner_id == current_user.id)
    )
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    
    await db.delete(share)
    await db.commit()


@router.get("/by-me", response_model=List[ShareResponse])
async def get_shares_by_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all shares I've created."""
    result = await db.execute(
        select(Share, User.username)
        .join(User, Share.shared_with_id == User.id)
        .where(Share.owner_id == current_user.id)
    )
    shares = result.all()
    
    return [
        ShareResponse(
            id=share.id,
            image_id=share.image_id,
            shared_with_username=username,
            permission=share.permission.value,
            created_at=share.created_at
        )
        for share, username in shares
    ]


@router.get("/with-me", response_model=List[SharedImageResponse])
async def get_shares_with_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all images shared with me."""
    result = await db.execute(
        select(Share, Image, User.username)
        .join(Image, Share.image_id == Image.id)
        .join(User, Share.owner_id == User.id)
        .where(Share.shared_with_id == current_user.id)
    )
    shares = result.all()
    
    return [
        SharedImageResponse(
            id=image.id,
            filename=image.filename,
            thumbnail_path=image.thumbnail_path,
            owner_username=username,
            permission=share.permission.value,
            shared_at=share.created_at
        )
        for share, image, username in shares
    ]
