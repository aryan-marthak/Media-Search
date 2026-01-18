"""
Pydantic models for request/response validation.
"""
from pydantic import BaseModel
from typing import List, Optional


class UploadResponse(BaseModel):
    """Response after uploading an image."""
    image_id: str
    file_path: str
    message: str


class SearchRequest(BaseModel):
    """Search query request."""
    query: str
    top_k: int = 10


class SearchResult(BaseModel):
    """Individual search result."""
    image_id: str
    image_url: str
    score: float
    global_score: float
    local_score: float


class SearchResponse(BaseModel):
    """Search results response."""
    query: str
    results: List[SearchResult]
    total: int


class GalleryImage(BaseModel):
    """Gallery image metadata."""
    id: str
    url: str
    uploaded_at: Optional[str] = None


class GalleryResponse(BaseModel):
    """Gallery listing response."""
    total: int
    images: List[GalleryImage]


class PersonCluster(BaseModel):
    """Face cluster (person) metadata."""
    id: str
    name: Optional[str] = None
    face_count: int
    representative_face_url: str
    created_at: str


class PeopleResponse(BaseModel):
    """List of all people (face clusters)."""
    total: int
    people: List[PersonCluster]


class LabelPersonRequest(BaseModel):
    """Request to label a person cluster."""
    name: str

