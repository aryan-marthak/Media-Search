from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User, FaceCluster, Face, Image
from auth import get_current_user

router = APIRouter()


class FaceClusterResponse(BaseModel):
    id: UUID
    name: Optional[str]
    representative_face_path: Optional[str]
    image_count: int


class FaceClusterUpdateRequest(BaseModel):
    name: str


class FaceImageResponse(BaseModel):
    id: UUID
    filename: str
    thumbnail_path: Optional[str]


@router.get("/clusters", response_model=List[FaceClusterResponse])
async def list_face_clusters(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all face clusters for the current user."""
    result = await db.execute(
        select(FaceCluster).where(FaceCluster.owner_id == current_user.id)
    )
    clusters = result.scalars().all()
    
    response = []
    for cluster in clusters:
        # Count images in cluster
        face_result = await db.execute(
            select(Face).where(Face.cluster_id == cluster.id)
        )
        face_count = len(face_result.scalars().all())
        
        response.append(FaceClusterResponse(
            id=cluster.id,
            name=cluster.name,
            representative_face_path=cluster.representative_face_path,
            image_count=face_count
        ))
    
    return response


@router.get("/clusters/{cluster_id}/images", response_model=List[FaceImageResponse])
async def get_cluster_images(
    cluster_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all images containing faces from this cluster."""
    # Verify cluster ownership
    result = await db.execute(
        select(FaceCluster).where(
            FaceCluster.id == cluster_id,
            FaceCluster.owner_id == current_user.id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    # Get images with faces in this cluster
    result = await db.execute(
        select(Image)
        .join(Face, Face.image_id == Image.id)
        .where(Face.cluster_id == cluster_id)
        .distinct()
    )
    images = result.scalars().all()
    
    return [
        FaceImageResponse(
            id=image.id,
            filename=image.filename,
            thumbnail_path=image.thumbnail_path
        )
        for image in images
    ]


@router.put("/clusters/{cluster_id}/name", response_model=FaceClusterResponse)
async def update_cluster_name(
    cluster_id: UUID,
    request: FaceClusterUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Assign or update a name for a face cluster."""
    result = await db.execute(
        select(FaceCluster).where(
            FaceCluster.id == cluster_id,
            FaceCluster.owner_id == current_user.id
        )
    )
    cluster = result.scalar_one_or_none()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    cluster.name = request.name
    await db.commit()
    await db.refresh(cluster)
    
    # Get face count
    face_result = await db.execute(
        select(Face).where(Face.cluster_id == cluster.id)
    )
    face_count = len(face_result.scalars().all())
    
    return FaceClusterResponse(
        id=cluster.id,
        name=cluster.name,
        representative_face_path=cluster.representative_face_path,
        image_count=face_count
    )


@router.get("/search")
async def search_by_person(
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search images by person name."""
    # Find matching clusters
    result = await db.execute(
        select(FaceCluster).where(
            FaceCluster.owner_id == current_user.id,
            FaceCluster.name.ilike(f"%{name}%")
        )
    )
    clusters = result.scalars().all()
    
    if not clusters:
        return {"results": [], "total": 0}
    
    # Get all images from matching clusters
    cluster_ids = [c.id for c in clusters]
    result = await db.execute(
        select(Image)
        .join(Face, Face.image_id == Image.id)
        .where(Face.cluster_id.in_(cluster_ids))
        .distinct()
    )
    images = result.scalars().all()
    
    return {
        "results": [
            {
                "id": img.id,
                "filename": img.filename,
                "thumbnail_path": img.thumbnail_path
            }
            for img in images
        ],
        "total": len(images)
    }
