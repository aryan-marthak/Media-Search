"""
Faces router — people clusters, labelling, clustering, VLM reprocessing.
All routes are scoped to the authenticated user.
"""
import uuid
from pathlib import Path
from PIL import Image

from fastapi import APIRouter, HTTPException, Depends

import config
from database import get_db_connection
from services.auth_service import get_current_user
from models import PersonCluster, PeopleResponse, GalleryImage, GalleryResponse, LabelPersonRequest

router = APIRouter()


@router.get("/people")
async def get_people(user_id: str = Depends(get_current_user)):
    """Get all face clusters for the current user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, representative_face_id, face_count, created_at
            FROM face_clusters
            WHERE user_id = %s
            ORDER BY face_count DESC
        """, (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        people = [
            PersonCluster(
                id=row["id"],
                name=row["name"],
                face_count=row["face_count"],
                representative_face_url=f"/faces/{row['representative_face_id']}.jpg",
                created_at=row["created_at"].isoformat() if row["created_at"] else "",
            )
            for row in rows
        ]
        return PeopleResponse(total=len(people), people=people)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get people: {str(e)}")


@router.post("/people/{cluster_id}/label")
async def label_person(
    cluster_id: str,
    request: LabelPersonRequest,
    user_id: str = Depends(get_current_user),
):
    """Label a face cluster. Merges with an existing cluster of the same name if one exists."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute(
            "SELECT id FROM face_clusters WHERE id = %s AND user_id = %s",
            (cluster_id, user_id),
        )
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Person cluster not found")

        # Check if another cluster already has this name for this user
        cursor.execute("""
            SELECT id FROM face_clusters
            WHERE name = %s AND user_id = %s AND id != %s
        """, (request.name, user_id, cluster_id))
        existing = cursor.fetchone()

        if existing:
            existing_id = existing["id"]
            cursor.execute(
                "UPDATE faces SET cluster_id = %s WHERE cluster_id = %s",
                (existing_id, cluster_id),
            )
            cursor.execute("""
                UPDATE face_clusters
                SET face_count = (SELECT COUNT(*) FROM faces WHERE cluster_id = %s), updated_at = NOW()
                WHERE id = %s
            """, (existing_id, existing_id))
            cursor.execute("DELETE FROM face_clusters WHERE id = %s", (cluster_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": f"Clusters merged into '{request.name}'", "merged_into": existing_id}

        cursor.execute("""
            UPDATE face_clusters SET name = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
        """, (request.name, cluster_id, user_id))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": f"Person labelled as '{request.name}'"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to label person: {str(e)}")


@router.get("/people/{cluster_id}/images")
async def get_person_images(
    cluster_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get all images containing a specific person (must belong to current user)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT i.id, i.file_path, i.created_at
            FROM images i
            JOIN faces f ON f.image_id = i.id
            WHERE f.cluster_id = %s AND i.user_id = %s
            ORDER BY i.created_at DESC
        """, (cluster_id, user_id))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        images = [
            GalleryImage(
                id=row["id"],
                url=f"/images/{user_id}/{row['id']}.jpg",
                uploaded_at=row["created_at"].isoformat() if row["created_at"] else None,
            )
            for row in rows
        ]
        return GalleryResponse(total=len(images), images=images)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get person images: {str(e)}")


@router.delete("/people/{cluster_id}")
async def delete_person(
    cluster_id: str,
    user_id: str = Depends(get_current_user),
):
    """Delete a face cluster and all its associated faces (must belong to current user)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM face_clusters WHERE id = %s AND user_id = %s",
            (cluster_id, user_id),
        )
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Person not found")

        cursor.execute("DELETE FROM faces WHERE cluster_id = %s", (cluster_id,))
        cursor.execute("DELETE FROM face_clusters WHERE id = %s", (cluster_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Person and all associated faces deleted"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete person: {str(e)}")


@router.post("/cluster-faces")
async def cluster_faces(user_id: str = Depends(get_current_user)):
    """Cluster all unassigned faces for the current user using DBSCAN."""
    try:
        from services.clustering_service import ClusteringService
        service = ClusteringService()
        stats = service.cluster_faces_for_user(user_id)
        return {"message": "Face clustering complete", "statistics": stats}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Clustering failed: {str(e)}")


@router.post("/reprocess-vlm")
async def reprocess_vlm_descriptions(user_id: str = Depends(get_current_user)):
    """Generate VLM descriptions for the current user's unprocessed images."""
    try:
        if not config.ENABLE_VLM:
            raise HTTPException(status_code=503, detail="VLM is disabled")

        from services.vlm_service import get_vlm_service
        vlm_service = get_vlm_service()
        if not vlm_service.is_available():
            raise HTTPException(status_code=503, detail="VLM service not available")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, file_path FROM images
            WHERE user_id = %s AND (vlm_processed = FALSE OR vlm_description IS NULL)
            ORDER BY created_at DESC
        """, (user_id,))
        images = cursor.fetchall()

        if not images:
            return {"message": "All images already have VLM descriptions", "processed": 0}

        processed = 0
        failed = 0
        for row in images:
            image_id = row["id"]
            try:
                image = Image.open(row["file_path"]).convert("RGB")
                description = vlm_service.generate_caption(image)
                if description:
                    cursor.execute(
                        "UPDATE images SET vlm_description = %s, vlm_processed = TRUE WHERE id = %s",
                        (description, image_id),
                    )
                    conn.commit()
                    processed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f">> Failed to process {image_id}: {str(e)}")
                failed += 1

        cursor.close()
        conn.close()
        return {"message": "VLM reprocessing complete", "processed": processed, "failed": failed, "total": len(images)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reprocessing failed: {str(e)}")
