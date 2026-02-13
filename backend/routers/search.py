from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query

from models import User
from auth import get_current_user
from services.search import normal_search, deep_search
from search_helper import get_search_helper

router = APIRouter()


class SearchResult(BaseModel):
    id: UUID
    filename: str
    thumbnail_path: Optional[str]
    score: float
    metadata: Optional[dict] = None


class SearchResponse(BaseModel):
    query: str  # The query actually used for search
    original_query: Optional[str] = None  # Set if query was auto-corrected
    did_you_mean: Optional[str] = None  # Alternative suggestion
    was_corrected: bool = False
    mode: str
    results: List[SearchResult]
    total: int


@router.get("/normal", response_model=SearchResponse)
async def search_normal(
    q: str = Query(..., min_length=1, description="Search query"),
    top_k: int = Query(20, ge=1, le=100),
    auto_correct: bool = Query(True, description="Automatically correct spelling"),
    current_user: User = Depends(get_current_user)
):
    """
    Fast embedding-based search.
    Uses SigLIP text encoder to match against image embeddings.
    Supports automatic spell correction.
    """
    helper = get_search_helper()
    original_query = q
    did_you_mean = None
    was_corrected = False
    
    if auto_correct:
        # Auto-correct spelling
        corrected_query, was_corrected = helper.correct_spelling(q)
        search_query = corrected_query
    else:
        # Just provide suggestion without auto-correcting
        search_query = q
        did_you_mean = helper.get_did_you_mean(q)
    
    results = await normal_search(search_query, str(current_user.id), top_k)
    
    return SearchResponse(
        query=search_query,
        original_query=original_query if was_corrected else None,
        did_you_mean=did_you_mean,
        was_corrected=was_corrected,
        mode="normal",
        results=results,
        total=len(results)
    )


@router.get("/deep", response_model=SearchResponse)
async def search_deep(
    q: str = Query(..., min_length=1, description="Search query"),
    top_k: int = Query(20, ge=1, le=50),
    auto_correct: bool = Query(True, description="Automatically correct spelling"),
    current_user: User = Depends(get_current_user)
):
    """
    Accurate search with VLM validation.
    1. Retrieves larger candidate pool via embeddings
    2. Applies soft metadata matching
    3. Validates top results with VLM
    Supports automatic spell correction.
    """
    helper = get_search_helper()
    original_query = q
    did_you_mean = None
    was_corrected = False
    
    if auto_correct:
        # Auto-correct spelling
        corrected_query, was_corrected = helper.correct_spelling(q)
        search_query = corrected_query
    else:
        # Just provide suggestion without auto-correcting
        search_query = q
        did_you_mean = helper.get_did_you_mean(q)
    
    results = await deep_search(search_query, str(current_user.id), top_k)
    
    return SearchResponse(
        query=search_query,
        original_query=original_query if was_corrected else None,
        did_you_mean=did_you_mean,
        was_corrected=was_corrected,
        mode="deep",
        results=results,
        total=len(results)
    )
