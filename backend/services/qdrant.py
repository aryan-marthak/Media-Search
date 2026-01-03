from typing import List, Dict, Any, Optional
from uuid import UUID
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models

from config import QDRANT_HOST, QDRANT_PORT, SIGLIP_EMBEDDING_DIM, FACE_EMBEDDING_DIM

# Global client cache
_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    """Get or initialize the Qdrant client (singleton)."""
    global _client
    
    if _client is None:
        _client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        print(f"✅ Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
    
    return _client


def get_images_collection_name(user_id: str) -> str:
    """Get the images collection name for a user."""
    return f"images_{user_id}"


def get_faces_collection_name(user_id: str) -> str:
    """Get the faces collection name for a user."""
    return f"faces_{user_id}"


async def ensure_collection(user_id: str, collection_type: str = "images") -> None:
    """Ensure a collection exists for the user."""
    client = get_qdrant_client()
    
    if collection_type == "images":
        collection_name = get_images_collection_name(user_id)
        vector_dim = SIGLIP_EMBEDDING_DIM
    else:
        collection_name = get_faces_collection_name(user_id)
        vector_dim = FACE_EMBEDDING_DIM
    
    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    
    if collection_name not in collection_names:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_dim,
                distance=models.Distance.COSINE
            )
        )
        print(f"✅ Created collection: {collection_name}")


async def upsert_image_embedding(
    user_id: str,
    image_id: str,
    embedding: np.ndarray,
    metadata: Dict[str, Any]
) -> None:
    """Insert or update an image embedding in Qdrant."""
    client = get_qdrant_client()
    collection_name = get_images_collection_name(user_id)
    
    # Ensure collection exists
    await ensure_collection(user_id, "images")
    
    # Prepare payload
    payload = {
        "image_id": image_id,
        **metadata
    }
    
    # Upsert point
    client.upsert(
        collection_name=collection_name,
        points=[
            models.PointStruct(
                id=image_id,
                vector=embedding.tolist(),
                payload=payload
            )
        ]
    )


async def search_images(
    user_id: str,
    query_embedding: np.ndarray,
    top_k: int = 20,
    score_threshold: Optional[float] = None
) -> List[Dict[str, Any]]:
    """Search for similar images using embedding."""
    client = get_qdrant_client()
    collection_name = get_images_collection_name(user_id)
    
    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    
    if collection_name not in collection_names:
        return []
    
    # Search
    results = client.search(
        collection_name=collection_name,
        query_vector=query_embedding.tolist(),
        limit=top_k,
        score_threshold=score_threshold
    )
    
    return [
        {
            "id": result.id,
            "score": result.score,
            "metadata": result.payload
        }
        for result in results
    ]


async def delete_image_embedding(user_id: str, image_id: str) -> None:
    """Delete an image embedding from Qdrant."""
    client = get_qdrant_client()
    collection_name = get_images_collection_name(user_id)
    
    try:
        client.delete(
            collection_name=collection_name,
            points_selector=models.PointIdsList(
                points=[image_id]
            )
        )
    except Exception:
        pass  # Collection or point may not exist


async def upsert_face_embedding(
    user_id: str,
    face_id: str,
    embedding: np.ndarray,
    metadata: Dict[str, Any]
) -> None:
    """Insert or update a face embedding in Qdrant."""
    client = get_qdrant_client()
    collection_name = get_faces_collection_name(user_id)
    
    # Ensure collection exists
    await ensure_collection(user_id, "faces")
    
    # Prepare payload
    payload = {
        "face_id": face_id,
        **metadata
    }
    
    # Upsert point
    client.upsert(
        collection_name=collection_name,
        points=[
            models.PointStruct(
                id=face_id,
                vector=embedding.tolist(),
                payload=payload
            )
        ]
    )


async def delete_face_embedding(user_id: str, face_id: str) -> None:
    """Delete a face embedding from Qdrant."""
    client = get_qdrant_client()
    collection_name = get_faces_collection_name(user_id)
    
    try:
        client.delete(
            collection_name=collection_name,
            points_selector=models.PointIdsList(
                points=[face_id]
            )
        )
    except Exception:
        pass  # Collection or point may not exist


async def search_similar_faces(
    user_id: str,
    query_embedding: np.ndarray,
    top_k: int = 10,
    score_threshold: float = 0.6
) -> List[Dict[str, Any]]:
    """Search for similar faces using embedding."""
    client = get_qdrant_client()
    collection_name = get_faces_collection_name(user_id)
    
    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    
    if collection_name not in collection_names:
        return []
    
    results = client.search(
        collection_name=collection_name,
        query_vector=query_embedding.tolist(),
        limit=top_k,
        score_threshold=score_threshold
    )
    
    return [
        {
            "id": result.id,
            "score": result.score,
            "metadata": result.payload
        }
        for result in results
    ]
