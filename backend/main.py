"""
Media Search Backend - FastAPI Application
CLIP-powered image search with local re-ranking and spell checking.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uuid
from pathlib import Path
from PIL import Image
import io
import numpy as np

import config
from database import init_databases, get_db_connection, get_qdrant_client
from embedding_service import get_embedding_service
from redis_cache import get_redis_cache
from search_helper import get_search_helper
from models import (
    UploadResponse, SearchRequest, SearchResponse, SearchResult,
    GalleryResponse, GalleryImage, PersonCluster, PeopleResponse, LabelPersonRequest
)

# Initialize FastAPI app
app = FastAPI(
    title="CLIP Media Search API",
    version="2.0.0",
    description="AI-powered image search using CLIP embeddings"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving images
app.mount("/images", StaticFiles(directory=str(config.STORAGE_DIR)), name="images")

# Mount static files for serving face thumbnails
faces_dir = config.STORAGE_DIR / "faces"
faces_dir.mkdir(parents=True, exist_ok=True)
app.mount("/faces", StaticFiles(directory=str(faces_dir)), name="faces")


@app.on_event("startup")
async def startup_event():
    """Initialize databases and load CLIP model on startup."""
    print(">> Starting CLIP Media Search API...")
    init_databases()
    get_embedding_service()  # Preload CLIP model
    get_redis_cache()  # Initialize Redis cache
    
    # Preload face detection models to avoid 30-second delay on first upload
    try:
        from face_service import get_face_service
        get_face_service()  # Preload face detection models
    except Exception as e:
        print(f">> Warning: Face detection preload failed: {str(e)}")
        print(f">> Face detection will still work, but first upload may be slower")
    
    print(">> API ready!")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "CLIP Media Search API is running",
        "model": f"{config.CLIP_MODEL} ({config.CLIP_PRETRAINED})"
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image and index it with CLIP.
    
    Workflow:
    1. Generate unique image_id
    2. Save image to local storage
    3. Compute CLIP embedding
    4. Store metadata in PostgreSQL
    5. Store vector in Qdrant
    6. Cache embedding in Redis
    """
    import time
    upload_start = time.time()
    
    try:
        # Generate unique ID
        image_id = str(uuid.uuid4())
        
        # Read and validate image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Handle EXIF orientation to prevent rotation issues
        from PIL import ImageOps
        image = ImageOps.exif_transpose(image)
        
        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Save to local storage
        file_path = config.STORAGE_DIR / f"{image_id}.jpg"
        image.save(file_path, "JPEG", quality=95)
        
        # Compute CLIP embedding
        clip_start = time.time()
        embedding_service = get_embedding_service()
        image_embedding = embedding_service.encode_image(image)
        clip_time = time.time() - clip_start
        
        # Store in PostgreSQL
        db_start = time.time()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO images (id, file_path) VALUES (%s, %s)",
            (image_id, str(file_path))
        )
        conn.commit()
        db_time = time.time() - db_start
        
        # Detect faces and extract embeddings (with error handling)
        faces = []
        face_start = time.time()
        try:
            from face_service import get_face_service
            face_service = get_face_service()
            faces = face_service.detect_and_extract_faces(image)
            
            # Store each detected face
            for face in faces:
                face_id = str(uuid.uuid4())
                bbox = face["bbox"]
                
                # Save face thumbnail
                face_service.save_face_thumbnail(face["face_crop"], face_id)
                
                # Store face in database
                cursor.execute(
                    """INSERT INTO faces 
                       (id, image_id, face_embedding, bbox_x, bbox_y, bbox_width, bbox_height, confidence)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (face_id, image_id, face["embedding"].tolist(), 
                     bbox[0], bbox[1], bbox[2], bbox[3], face["confidence"])
                )
            conn.commit()
        except Exception as e:
            print(f">> Face detection error (upload will continue): {str(e)}")
            import traceback
            traceback.print_exc()
            # Don't fail the upload, just skip face detection

        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Generate VLM description for Deep Search (with error handling)
        vlm_description = None
        if config.ENABLE_VLM:
            try:
                from vlm_service import get_vlm_service
                vlm_service = get_vlm_service()
                
                if vlm_service.is_available():
                    print(f">> Generating VLM description for {image_id}...")
                    vlm_description = vlm_service.generate_caption(image)
                    
                    if vlm_description:
                        # Store VLM description in database
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE images SET vlm_description = %s, vlm_processed = TRUE WHERE id = %s",
                            (vlm_description, image_id)
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()
                        print(f">> VLM description: {vlm_description[:100]}...")
            except Exception as e:
                print(f">> ⚠️  VLM description generation failed (upload will continue): {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            print(">> VLM is disabled (set ENABLE_VLM=true to enable Deep Search)")
        
        # Store in Qdrant
        qdrant_client = get_qdrant_client()
        qdrant_client.upsert(
            collection_name=config.QDRANT_COLLECTION,
            points=[{
                "id": image_id,
                "vector": image_embedding.tolist(),
                "payload": {"image_id": image_id}
            }]
        )
        
        # Cache embedding in Redis
        redis_cache = get_redis_cache()
        redis_cache.set_embedding(image_id, image_embedding)
        
        total_time = time.time() - upload_start
        face_time = time.time() - face_start
        print(f">> Upload timing - CLIP: {clip_time:.2f}s, Face: {face_time:.2f}s, DB: {db_time:.2f}s, Total: {total_time:.2f}s")
        
        message = f"Image uploaded and indexed with CLIP. Detected {len(faces)} face(s)."
        if vlm_description:
            message += " Deep Search enabled."
        
        return UploadResponse(
            image_id=image_id,
            file_path=str(file_path),
            message=message
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/gallery", response_model=GalleryResponse)
async def get_gallery():
    """Get all images in the gallery with metadata."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, file_path, created_at
            FROM images 
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        images = []
        for row in rows:
            images.append(GalleryImage(
                id=row['id'],
                url=f"/images/{row['id']}{Path(row['file_path']).suffix}",
                uploaded_at=row['created_at'].isoformat() if row['created_at'] else None
            ))
        
        return GalleryResponse(
            total=len(images),
            images=images
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch gallery: {str(e)}")


@app.delete("/images")
async def delete_images(image_ids: list[str]):
    """Delete multiple images by their IDs."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        qdrant_client = get_qdrant_client()
        redis_cache = get_redis_cache()
        
        deleted_count = 0
        
        for image_id in image_ids:
            # Get file path
            cursor.execute("SELECT file_path FROM images WHERE id = %s", (image_id,))
            row = cursor.fetchone()
            
            if row:
                # Delete file from disk
                file_path = Path(row['file_path'])
                if file_path.exists():
                    file_path.unlink()
                
                # Delete from PostgreSQL
                cursor.execute("DELETE FROM images WHERE id = %s", (image_id,))
                
                # Delete from Qdrant
                qdrant_client.delete(
                    collection_name=config.QDRANT_COLLECTION,
                    points_selector=[image_id]
                )
                
                # Delete from Redis cache
                redis_cache.delete_embedding(image_id)
                
                deleted_count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "message": f"Successfully deleted {deleted_count} image(s)",
            "deleted_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@app.post("/spell-check")
async def spell_check(query: dict):
    """Check spelling and get corrections for search query."""
    try:
        search_helper = get_search_helper()
        
        original_query = query.get("query", "")
        corrected_query, was_corrected = search_helper.correct_spelling(original_query)
        did_you_mean = search_helper.get_did_you_mean(original_query)
        
        return {
            "original": original_query,
            "corrected": corrected_query,
            "was_corrected": was_corrected,
            "did_you_mean": did_you_mean
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spell check failed: {str(e)}")


@app.get("/search-suggestions")
async def get_search_suggestions(query: str = ""):
    """Get alternative search term suggestions."""
    try:
        search_helper = get_search_helper()
        suggestions = search_helper.get_suggestions(query)
        
        return {
            "suggestions": suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@app.post("/search", response_model=SearchResponse)
async def search_images(request: SearchRequest):
    """
    Search images using person names or CLIP semantic search.
    
    Strategy:
    1. Check if query matches a person name (face cluster)
    2. If match found, return all images containing that person
    3. Otherwise, use CLIP semantic search
    """
    try:
        # First, check if query matches a person name
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Search for person by name (case-insensitive, partial match)
        cursor.execute("""
            SELECT id, name FROM face_clusters 
            WHERE LOWER(name) LIKE LOWER(%s)
            LIMIT 1
        """, (f"%{request.query}%",))
        
        person_match = cursor.fetchone()
        
        if person_match:
            # Found a person match - return all images containing this person
            cluster_id = person_match['id']
            person_name = person_match['name']
            
            print(f">> Person search: '{request.query}' matched '{person_name}'")
            
            try:
                cursor.execute("""
                    SELECT DISTINCT i.id, i.file_path, i.created_at
                    FROM images i
                    JOIN faces f ON f.image_id = i.id
                    WHERE f.cluster_id = %s
                    ORDER BY i.created_at DESC
                """, (cluster_id,))
                
                rows = cursor.fetchall()
                print(f">> Found {len(rows)} images for person '{person_name}'")
            except Exception as e:
                print(f">> Error executing person search query: {str(e)}")
                import traceback
                traceback.print_exc()
                raise
            
            cursor.close()
            conn.close()
            
            results = []
            for row in rows:
                results.append(SearchResult(
                    image_id=row['id'],
                    image_url=f"/images/{row['id']}.jpg",
                    score=1.0,  # Perfect match for person search
                    global_score=1.0,
                    local_score=1.0
                ))
            
            return SearchResponse(
                query=request.query,
                results=results,
                total=len(results)
            )
        
        cursor.close()
        conn.close()
        
        # No person match - proceed with CLIP semantic search
        embedding_service = get_embedding_service()
        qdrant_client = get_qdrant_client()
        
        # Main query
        main_query = request.query
        
        # Generate query variations for better matching
        query_variations = [
            main_query,
            f"a photo of {main_query}",
            f"{main_query} in the image"
        ]
        
        # Encode all query variations
        query_embeddings = []
        for query_var in query_variations:
            emb = embedding_service.encode_text(query_var)
            query_embeddings.append(emb)
        
        # Average the embeddings for robust matching
        avg_query_embedding = np.mean(query_embeddings, axis=0)
        # Re-normalize
        avg_query_embedding = avg_query_embedding / np.linalg.norm(avg_query_embedding)
        
        # Search Qdrant with averaged query
        search_results = qdrant_client.search(
            collection_name=config.QDRANT_COLLECTION,
            query_vector=avg_query_embedding.tolist(),
            limit=config.TOP_K if not config.ENABLE_LOCAL_RERANKING else 30,
            score_threshold=config.SCORE_THRESHOLD
        )
        
        # Local re-ranking if enabled
        if config.ENABLE_LOCAL_RERANKING:
            reranked_results = []
            
            for result in search_results:
                image_id = result.id
                global_score = result.score
                
                # Load image for local scoring
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT file_path FROM images WHERE id = %s", (image_id,))
                row = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if not row:
                    continue
                
                file_path = Path(row['file_path'])
                if not file_path.exists():
                    continue
                
                # Load image
                image = Image.open(file_path)
                
                # Zero-shot classification filter (if enabled)
                if config.ENABLE_ZERO_SHOT_FILTER:
                    contains_concept, zs_confidence = embedding_service.zero_shot_classify(
                        image, main_query, config.ZERO_SHOT_THRESHOLD
                    )
                    
                    if not contains_concept:
                        continue
                
                # Compute local score
                local_score = embedding_service.compute_local_score(image, avg_query_embedding)
                
                # Combined score
                final_score = (config.GLOBAL_WEIGHT * global_score + 
                              config.LOCAL_WEIGHT * local_score)
                
                reranked_results.append({
                    'image_id': image_id,
                    'score': final_score,
                    'global_score': global_score,
                    'local_score': local_score
                })
            
            # Sort by final score
            reranked_results.sort(key=lambda x: x['score'], reverse=True)
            
            # Diversity-based re-ranking
            diverse_results = []
            used_embeddings = []
            
            redis_cache = get_redis_cache()
            
            for item in reranked_results:
                image_id = item['image_id']
                
                # Try to get embedding from Redis cache
                img_embedding = redis_cache.get_embedding(image_id)
                
                # If not cached, load and encode image
                if img_embedding is None:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT file_path FROM images WHERE id = %s", (image_id,))
                    row = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    
                    if not row:
                        continue
                    
                    file_path = Path(row['file_path'])
                    if not file_path.exists():
                        continue
                    
                    image = Image.open(file_path)
                    img_embedding = embedding_service.encode_image(image)
                    
                    # Cache it for next time
                    redis_cache.set_embedding(image_id, img_embedding)
                
                # Check diversity
                is_diverse = True
                for used_emb in used_embeddings:
                    similarity = np.dot(img_embedding, used_emb)
                    if similarity > 0.95:  # Too similar
                        is_diverse = False
                        break
                
                if is_diverse:
                    diverse_results.append(item)
                    used_embeddings.append(img_embedding)
                
                # Stop when we have enough
                if len(diverse_results) >= request.top_k:
                    break
            
            # Format results
            results = []
            for item in diverse_results:
                results.append(SearchResult(
                    image_id=item['image_id'],
                    image_url=f"/images/{item['image_id']}.jpg",
                    score=item['score'],
                    global_score=item['global_score'],
                    local_score=item['local_score']
                ))
        else:
            # No local re-ranking
            results = []
            for result in search_results:
                image_id = result.id
                score = result.score
                
                results.append(SearchResult(
                    image_id=image_id,
                    image_url=f"/images/{image_id}.jpg",
                    score=score,
                    global_score=score,
                    local_score=0.0
                ))
            
            results = results[:request.top_k]
        
        return SearchResponse(
            query=request.query,
            results=results,
            total=len(results)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/deep-search", response_model=SearchResponse)
async def deep_search_images(request: SearchRequest):
    """
    Deep Search using VLM descriptions for detailed, contextual queries.
    
    Strategy:
    1. Retrieve all VLM descriptions from database
    2. Encode query and descriptions as text embeddings
    3. Compute cosine similarity
    4. Return top-k matches
    """
    try:
        from vlm_service import get_vlm_service
        vlm_service = get_vlm_service()
        
        if not vlm_service.is_available():
            raise HTTPException(
                status_code=503, 
                detail="Deep Search unavailable: VLM model not loaded"
            )
        
        embedding_service = get_embedding_service()
        
        # Encode query as text
        query_embedding = embedding_service.encode_text(request.query)
        
        # Retrieve all images with VLM descriptions
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, file_path, vlm_description, created_at
            FROM images
            WHERE vlm_processed = TRUE AND vlm_description IS NOT NULL
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not rows:
            return SearchResponse(
                query=request.query,
                results=[],
                total=0
            )
        
        # Compute similarity scores
        results_with_scores = []
        for row in rows:
            image_id = row['id']
            description = row['vlm_description']
            
            # Encode description as text
            desc_embedding = embedding_service.encode_text(description)
            
            # Compute cosine similarity
            similarity = np.dot(query_embedding, desc_embedding)
            
            # Filter by threshold
            if similarity >= config.SCORE_THRESHOLD:
                results_with_scores.append({
                    'image_id': image_id,
                    'score': float(similarity),
                    'description': description
                })
        
        # Sort by score
        results_with_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # Take top-k
        top_results = results_with_scores[:request.top_k]
        
        # Format response
        results = []
        for item in top_results:
            results.append(SearchResult(
                image_id=item['image_id'],
                image_url=f"/images/{item['image_id']}.jpg",
                score=item['score'],
                global_score=item['score'],
                local_score=0.0
            ))
        
        return SearchResponse(
            query=request.query,
            results=results,
            total=len(results)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deep Search failed: {str(e)}")


@app.get("/people")
async def get_people():
    """Get all face clusters (people) with metadata."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, representative_face_id, face_count, created_at
            FROM face_clusters
            ORDER BY face_count DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        people = []
        for row in rows:
            people.append(PersonCluster(
                id=row['id'],
                name=row['name'],
                face_count=row['face_count'],
                representative_face_url=f"/faces/{row['representative_face_id']}.jpg",
                created_at=row['created_at'].isoformat() if row['created_at'] else ""
            ))
        
        return PeopleResponse(
            total=len(people),
            people=people
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get people: {str(e)}")


@app.post("/people/{cluster_id}/label")
async def label_person(cluster_id: str, request: LabelPersonRequest):
    """Assign a name to a face cluster. If another cluster has the same name, merge them."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if another cluster already has this name
        cursor.execute("""
            SELECT id, face_count, representative_face_id 
            FROM face_clusters 
            WHERE name = %s AND id != %s
        """, (request.name, cluster_id))
        
        existing_cluster = cursor.fetchone()
        
        if existing_cluster:
            # Merge clusters: move all faces from current cluster to existing cluster
            existing_cluster_id = existing_cluster['id']
            
            print(f">> Merging cluster {cluster_id} into {existing_cluster_id} (both named '{request.name}')")
            
            # Move all faces from current cluster to existing cluster
            cursor.execute("""
                UPDATE faces 
                SET cluster_id = %s 
                WHERE cluster_id = %s
            """, (existing_cluster_id, cluster_id))
            
            # Update face count in existing cluster
            cursor.execute("""
                UPDATE face_clusters 
                SET face_count = (
                    SELECT COUNT(*) FROM faces WHERE cluster_id = %s
                ),
                updated_at = NOW()
                WHERE id = %s
            """, (existing_cluster_id, existing_cluster_id))
            
            # Delete the now-empty cluster
            cursor.execute("DELETE FROM face_clusters WHERE id = %s", (cluster_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                "message": f"Clusters merged into '{request.name}'",
                "merged_into": existing_cluster_id
            }
        else:
            # No existing cluster with this name, just update the name
            cursor.execute("""
                UPDATE face_clusters
                SET name = %s, updated_at = NOW()
                WHERE id = %s
            """, (request.name, cluster_id))
            
            if cursor.rowcount == 0:
                cursor.close()
                conn.close()
                raise HTTPException(status_code=404, detail="Person cluster not found")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {"message": f"Person labeled as '{request.name}'"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to label person: {str(e)}")


@app.get("/people/{cluster_id}/images")
async def get_person_images(cluster_id: str):
    """Get all images containing a specific person."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT i.id, i.file_path, i.created_at
            FROM images i
            JOIN faces f ON f.image_id = i.id
            WHERE f.cluster_id = %s
            ORDER BY i.created_at DESC
        """, (cluster_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        images = []
        for row in rows:
            images.append(GalleryImage(
                id=row['id'],
                url=f"/images/{row['id']}.jpg",
                uploaded_at=row['created_at'].isoformat() if row['created_at'] else None
            ))
        
        return GalleryResponse(
            total=len(images),
            images=images
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get person images: {str(e)}")


@app.delete("/people/{cluster_id}")
async def delete_person(cluster_id: str):
    """Delete a face cluster and permanently delete all its associated faces."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if cluster exists
        cursor.execute("SELECT id FROM face_clusters WHERE id = %s", (cluster_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Person not found")
        
        # PERMANENTLY delete all faces in this cluster (not just unassign)
        cursor.execute("""
            DELETE FROM faces 
            WHERE cluster_id = %s
        """, (cluster_id,))
        
        # Delete the cluster
        cursor.execute("DELETE FROM face_clusters WHERE id = %s", (cluster_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"message": "Person and all associated faces deleted permanently"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete person: {str(e)}")


@app.post("/cluster-faces")
async def cluster_faces():
    """Cluster all unassigned faces using DBSCAN algorithm."""
    try:
        from clustering_service import get_clustering_service
        clustering_service = get_clustering_service()
        stats = clustering_service.cluster_faces()
        
        return {
            "message": "Face clustering complete",
            "statistics": stats
        }
    except Exception as e:
        print(f">> Clustering error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Clustering failed: {str(e)}")


@app.post("/reprocess-vlm")
async def reprocess_vlm_descriptions():
    """Generate VLM descriptions for all images that don't have them."""
    try:
        if not config.ENABLE_VLM:
            raise HTTPException(status_code=503, detail="VLM is disabled")
        
        from vlm_service import get_vlm_service
        vlm_service = get_vlm_service()
        
        if not vlm_service.is_available():
            raise HTTPException(status_code=503, detail="VLM service not available")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, file_path 
            FROM images 
            WHERE vlm_processed = FALSE OR vlm_description IS NULL
            ORDER BY created_at DESC
        """)
        images = cursor.fetchall()
        
        if not images:
            return {"message": "All images already have VLM descriptions", "processed": 0}
        
        processed = 0
        failed = 0
        
        for row in images:
            image_id = row['id']
            file_path = row['file_path']
            
            try:
                from PIL import Image
                image = Image.open(file_path).convert("RGB")
                description = vlm_service.generate_caption(image)
                
                if description:
                    cursor.execute(
                        "UPDATE images SET vlm_description = %s, vlm_processed = TRUE WHERE id = %s",
                        (description, image_id)
                    )
                    conn.commit()
                    processed += 1
                    print(f">> Processed {image_id}: {description[:80]}...")
                else:
                    failed += 1
            except Exception as e:
                print(f">> Failed to process {image_id}: {str(e)}")
                failed += 1
                continue
        
        cursor.close()
        conn.close()
        
        return {
            "message": "VLM reprocessing complete",
            "processed": processed,
            "failed": failed,
            "total": len(images)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reprocessing failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)
