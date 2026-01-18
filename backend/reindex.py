"""
Reindex utility - Recompute embeddings for all images.
Useful after changing CLIP model or fixing corrupted data.
"""
from pathlib import Path
from PIL import Image
import sys

import config
from database import get_db_connection, get_qdrant_client
from embedding_service import get_embedding_service
from redis_cache import get_redis_cache


def reindex_all_images():
    """Reindex all images in the database."""
    print(">> Starting reindex process...")
    
    # Get services
    embedding_service = get_embedding_service()
    qdrant_client = get_qdrant_client()
    redis_cache = get_redis_cache()
    
    # Get all images from database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, file_path FROM images")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    total = len(rows)
    print(f">> Found {total} images to reindex")
    
    success_count = 0
    error_count = 0
    
    for idx, row in enumerate(rows, 1):
        image_id = row['id']
        file_path = Path(row['file_path'])
        
        print(f"[{idx}/{total}] Processing {image_id}...", end=" ")
        
        try:
            if not file_path.exists():
                print("SKIP (file not found)")
                error_count += 1
                continue
            
            # Load image
            image = Image.open(file_path)
            
            # Compute embedding
            embedding = embedding_service.encode_image(image)
            
            # Update Qdrant
            qdrant_client.upsert(
                collection_name=config.QDRANT_COLLECTION,
                points=[{
                    "id": image_id,
                    "vector": embedding.tolist(),
                    "payload": {"image_id": image_id}
                }]
            )
            
            # Update Redis cache
            redis_cache.set_embedding(image_id, embedding)
            
            print("OK")
            success_count += 1
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
            error_count += 1
    
    print(f"\n>> Reindex complete!")
    print(f"   Success: {success_count}")
    print(f"   Errors: {error_count}")


if __name__ == "__main__":
    reindex_all_images()
