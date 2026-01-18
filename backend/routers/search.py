from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query

from models import User
from auth import get_current_user
from services.search import normal_search, deep_search

router = APIRouter()


class SearchResult(BaseModel):
    id: UUID
    filename: str
    thumbnail_path: Optional[str]
    score: float
    metadata: Optional[dict] = None


class SearchResponse(BaseModel):
    query: str
    mode: str
    results: List[SearchResult]
    total: int


@router.get("/normal", response_model=SearchResponse)
async def search_normal(
    q: str = Query(..., min_length=1, description="Search query"),
    top_k: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """
    Fast embedding-based search.
    Uses SigLIP text encoder to match against image embeddings.
    """
    results = await normal_search(q, str(current_user.id), top_k)
    
    return SearchResponse(
        query=q,
        mode="normal",
        results=results,
        total=len(results)
    )


@router.get("/deep", response_model=SearchResponse)
async def search_deep(
    q: str = Query(..., min_length=1, description="Search query"),
    top_k: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """
    Accurate search with VLM validation.
    1. Retrieves larger candidate pool via embeddings
    2. Applies soft metadata matching
    3. Validates top results with VLM
    """
    results = await deep_search(q, str(current_user.id), top_k)
    
    return SearchResponse(
        query=q,
        mode="deep",
        results=results,
        total=len(results)
    )
