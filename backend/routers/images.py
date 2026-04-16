"""
Images router — upload, gallery, delete, image detail.
All routes are scoped to the authenticated user.
"""
import uuid
import time
from pathlib import Path
from PIL import Image, ImageOps
import io
import numpy as np

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

import config
from database import get_db_connection, get_qdrant_client
from services.embedding_service import get_embedding_service
from services.redis_cache import get_redis_cache
from services.auth_service import get_current_user
from models import UploadResponse, GalleryResponse, GalleryImage

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    """Upload an image and index it with CLIP, scoped to the current user."""
    upload_start = time.time()
    try:
        image_id = str(uuid.uuid4())

        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        image = ImageOps.exif_transpose(image)
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Store files in per-user subdirectory
        user_storage = config.STORAGE_DIR / user_id
        user_storage.mkdir(parents=True, exist_ok=True)
        file_path = user_storage / f"{image_id}.jpg"
        image.save(file_path, "JPEG", quality=95)

        # Compute CLIP embedding
        clip_start = time.time()
        embedding_service = get_embedding_service()
        image_embedding = embedding_service.encode_image(image)
        clip_time = time.time() - clip_start

        # Store metadata in PostgreSQL
        db_start = time.time()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO images (id, user_id, file_path) VALUES (%s, %s, %s)",
            (image_id, user_id, str(file_path)),
        )
        conn.commit()
        db_time = time.time() - db_start

        # Detect faces
        faces = []
        face_start = time.time()
        try:
            from services.face_service import get_face_service
            face_service = get_face_service()
            faces = face_service.detect_and_extract_faces(image)

            for face in faces:
                face_id = str(uuid.uuid4())
                bbox = face["bbox"]
                face_service.save_face_thumbnail(face["face_crop"], face_id)
                cursor.execute(
                    """INSERT INTO faces
                       (id, image_id, face_embedding, bbox_x, bbox_y, bbox_width, bbox_height, confidence)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (face_id, image_id, face["embedding"].tolist(),
                     bbox[0], bbox[1], bbox[2], bbox[3], face["confidence"]),
                )
            conn.commit()
        except Exception as e:
            print(f">> Face detection error (upload will continue): {str(e)}")

        # VLM description
        vlm_description = None
        if config.ENABLE_VLM:
            try:
                from services.vlm_service import get_vlm_service
                vlm_service = get_vlm_service()
                if vlm_service.is_available():
                    print(f">> Generating VLM description for {image_id}...")
                    vlm_description = vlm_service.generate_caption(image)
                    if vlm_description:
                        cursor.execute(
                            "UPDATE images SET vlm_description = %s, vlm_processed = TRUE WHERE id = %s",
                            (vlm_description, image_id),
                        )
                        conn.commit()
                        print(f">> VLM description: {vlm_description[:100]}...")
            except Exception as e:
                print(f">> VLM description failed (upload will continue): {str(e)}")

        cursor.close()
        conn.close()

        # Upsert into Qdrant — include user_id in payload for filtering
        qdrant_client = get_qdrant_client()
        qdrant_client.upsert(
            collection_name=config.QDRANT_COLLECTION,
            points=[{
                "id": image_id,
                "vector": image_embedding.tolist(),
                "payload": {"image_id": image_id, "user_id": user_id},
            }],
        )

        # Cache embedding
        redis_cache = get_redis_cache()
        redis_cache.set_embedding(image_id, image_embedding)

        total_time = time.time() - upload_start
        face_time = time.time() - face_start
        print(f">> Upload timing - CLIP: {clip_time:.2f}s, Face: {face_time:.2f}s, DB: {db_time:.2f}s, Total: {total_time:.2f}s")

        message = f"Image uploaded and indexed. Detected {len(faces)} face(s)."
        if vlm_description:
            message += " Deep Search enabled."

        return UploadResponse(
            image_id=image_id,
            file_path=str(file_path),
            message=message,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/gallery", response_model=GalleryResponse)
async def get_gallery(user_id: str = Depends(get_current_user)):
    """Get all images for the current user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, file_path, vlm_description, created_at
            FROM images
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))
        rows = cursor.fetchall()

        images = []
        for row in rows:
            image_id = row["id"]
            cursor.execute("""
                SELECT DISTINCT fc.name, fc.id
                FROM faces f
                JOIN face_clusters fc ON f.cluster_id = fc.id
                WHERE f.image_id = %s
                ORDER BY fc.name
            """, (image_id,))
            face_rows = cursor.fetchall()
            face_names = [
                fr["name"] if fr["name"] else f"Person {fr['id'][:8]}"
                for fr in face_rows
            ]

            images.append(GalleryImage(
                id=row["id"],
                url=f"/images/{user_id}/{row['id']}.jpg",
                uploaded_at=row["created_at"].isoformat() if row["created_at"] else None,
                description=row["vlm_description"],
                faces=face_names,
            ))

        cursor.close()
        conn.close()
        return GalleryResponse(total=len(images), images=images)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch gallery: {str(e)}")


@router.delete("/images")
async def delete_images(
    image_ids: list[str],
    user_id: str = Depends(get_current_user),
):
    """Delete the current user's images by ID."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        qdrant_client = get_qdrant_client()
        redis_cache = get_redis_cache()

        deleted_count = 0
        for image_id in image_ids:
            # Only delete if the image belongs to this user
            cursor.execute(
                "SELECT file_path FROM images WHERE id = %s AND user_id = %s",
                (image_id, user_id),
            )
            row = cursor.fetchone()
            if row:
                file_path = Path(row["file_path"])
                if file_path.exists():
                    file_path.unlink()

                cursor.execute("DELETE FROM images WHERE id = %s", (image_id,))
                qdrant_client.delete(
                    collection_name=config.QDRANT_COLLECTION,
                    points_selector=[image_id],
                )
                redis_cache.delete_embedding(image_id)
                deleted_count += 1

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": f"Successfully deleted {deleted_count} image(s)", "deleted_count": deleted_count}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@router.get("/image-details/{image_id}")
async def get_image_details(
    image_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get detailed metadata for one of the current user's images."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, file_path, vlm_description, vlm_processed, created_at
            FROM images
            WHERE id = %s AND user_id = %s
        """, (image_id, user_id))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Image not found")

        return {
            "id": row["id"],
            "image_url": f"/images/{user_id}/{row['id']}.jpg",
            "vlm_description": row["vlm_description"],
            "vlm_processed": row["vlm_processed"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get image details: {str(e)}")
