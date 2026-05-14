"""
Search router — CLIP semantic search, deep search, spell-check, suggestions.
All search results are scoped to the authenticated user.
"""
import numpy as np
from pathlib import Path
from PIL import Image

from fastapi import APIRouter, HTTPException, Depends
from qdrant_client.models import Filter, FieldCondition, MatchValue

import config
from database import get_db_connection, get_qdrant_client
from services.embedding_service import get_embedding_service
from services.redis_cache import get_redis_cache
from services.search_helper import get_search_helper
from services.auth_service import get_current_user
from models import SearchRequest, SearchResponse, SearchResult

router = APIRouter()


@router.post("/spell-check")
async def spell_check(
    query: dict,
    user_id: str = Depends(get_current_user),
):
    """Check spelling and get corrections for a search query."""
    try:
        search_helper = get_search_helper()
        original_query = query.get("query", "")
        corrected_query, was_corrected = search_helper.correct_spelling(original_query)
        did_you_mean = search_helper.get_did_you_mean(original_query)
        return {
            "original": original_query,
            "corrected": corrected_query,
            "was_corrected": was_corrected,
            "did_you_mean": did_you_mean,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spell check failed: {str(e)}")


@router.get("/search-suggestions")
async def get_search_suggestions(
    query: str = "",
    user_id: str = Depends(get_current_user),
):
    """Get alternative search term suggestions."""
    try:
        search_helper = get_search_helper()
        suggestions = search_helper.get_suggestions(query)
        return {"suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_images(
    request: SearchRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Search images by person name or CLIP semantic similarity.
    Results are scoped to the current user.
    """
    try:
        redis_cache = get_redis_cache()

        # --- Query result cache hit: skip entire pipeline ---
        cached = redis_cache.get_search_results(request.query, user_id)
        if cached:
            results = [SearchResult(**r) for r in cached]
            print(f">> Cache hit for query: '{request.query}'")
            return SearchResponse(query=request.query, results=results, total=len(results))

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if query matches a person name the user has labelled
        cursor.execute("""
            SELECT id, name FROM face_clusters
            WHERE user_id = %s AND LOWER(name) LIKE LOWER(%s)
            LIMIT 1
        """, (user_id, f"%{request.query}%"))
        person_match = cursor.fetchone()

        if person_match:
            cluster_id = person_match["id"]
            person_name = person_match["name"]
            print(f">> Person search: '{request.query}' matched '{person_name}'")

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

            results = [
                SearchResult(
                    image_id=row["id"],
                    image_url=f"/images/{user_id}/{row['id']}.jpg",
                    score=1.0,
                    global_score=1.0,
                    local_score=1.0,
                )
                for row in rows
            ]
            redis_cache.set_search_results(request.query, user_id, [r.model_dump() for r in results])
            return SearchResponse(query=request.query, results=results, total=len(results))

        cursor.close()
        conn.close()

        # CLIP semantic search — filter by user_id in Qdrant payload
        embedding_service = get_embedding_service()
        qdrant_client = get_qdrant_client()

        query_variations = [
            request.query,
            f"a photo of {request.query}",
            f"{request.query} in the image",
        ]
        query_embeddings = [embedding_service.encode_text(q) for q in query_variations]
        avg_query_embedding = np.mean(query_embeddings, axis=0)
        avg_query_embedding = avg_query_embedding / np.linalg.norm(avg_query_embedding)

        user_filter = Filter(
            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        )

        search_results = qdrant_client.search(
            collection_name=config.QDRANT_COLLECTION,
            query_vector=avg_query_embedding.tolist(),
            query_filter=user_filter,
            limit=config.TOP_K if not config.ENABLE_LOCAL_RERANKING else 30,
            score_threshold=config.SCORE_THRESHOLD,
        )

        if config.ENABLE_LOCAL_RERANKING:
            reranked_results = []
            for result in search_results:
                image_id = result.id
                global_score = result.score

                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT file_path FROM images WHERE id = %s AND user_id = %s", (image_id, user_id))
                row = cursor.fetchone()
                cursor.close()
                conn.close()

                if not row:
                    continue
                file_path = Path(row["file_path"])
                if not file_path.exists():
                    continue

                image = Image.open(file_path)

                if config.ENABLE_ZERO_SHOT_FILTER:
                    contains_concept, zs_confidence = embedding_service.zero_shot_classify(
                        image, request.query, config.ZERO_SHOT_THRESHOLD
                    )
                    if not contains_concept:
                        continue

                local_score = embedding_service.compute_local_score(image, avg_query_embedding)
                final_score = config.GLOBAL_WEIGHT * global_score + config.LOCAL_WEIGHT * local_score

                reranked_results.append({
                    "image_id": image_id,
                    "score": final_score,
                    "global_score": global_score,
                    "local_score": local_score,
                })

            reranked_results.sort(key=lambda x: x["score"], reverse=True)

            diverse_results = []
            used_embeddings = []

            for item in reranked_results:
                image_id = item["image_id"]
                img_embedding = redis_cache.get_embedding(image_id)

                if img_embedding is None:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT file_path FROM images WHERE id = %s AND user_id = %s", (image_id, user_id))
                    row = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    if not row:
                        continue
                    file_path = Path(row["file_path"])
                    if not file_path.exists():
                        continue
                    image = Image.open(file_path)
                    img_embedding = embedding_service.encode_image(image)
                    redis_cache.set_embedding(image_id, img_embedding)

                is_diverse = all(np.dot(img_embedding, used) <= 0.95 for used in used_embeddings)
                if is_diverse:
                    diverse_results.append(item)
                    used_embeddings.append(img_embedding)

                if len(diverse_results) >= request.top_k:
                    break

            results = [
                SearchResult(
                    image_id=item["image_id"],
                    image_url=f"/images/{user_id}/{item['image_id']}.jpg",
                    score=item["score"],
                    global_score=item["global_score"],
                    local_score=item["local_score"],
                )
                for item in diverse_results
            ]
        else:
            results = [
                SearchResult(
                    image_id=r.id,
                    image_url=f"/images/{user_id}/{r.id}.jpg",
                    score=r.score,
                    global_score=r.score,
                    local_score=0.0,
                )
                for r in search_results
            ][:request.top_k]

        redis_cache.set_search_results(request.query, user_id, [r.model_dump() for r in results])
        return SearchResponse(query=request.query, results=results, total=len(results))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/deep-search", response_model=SearchResponse)
async def deep_search_images(
    request: SearchRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Hybrid BM25 + CLIP deep search on VLM descriptions.
    Scoped to the current user's images.
    """
    try:
        redis_cache = get_redis_cache()

        # --- Query result cache hit: skip entire pipeline ---
        cached = redis_cache.get_search_results(request.query, user_id)
        if cached:
            results = [SearchResult(**r) for r in cached]
            print(f">> Cache hit for deep query: '{request.query}'")
            return SearchResponse(query=request.query, results=results, total=len(results))

        from services.vlm_service import get_vlm_service
        from services.bm25_matcher import get_bm25_matcher

        vlm_service = get_vlm_service()
        if not vlm_service.is_available():
            raise HTTPException(status_code=503, detail="Deep Search unavailable: VLM model not loaded")

        embedding_service = get_embedding_service()
        bm25_matcher = get_bm25_matcher()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, file_path, vlm_description, created_at
            FROM images
            WHERE user_id = %s AND vlm_processed = TRUE AND vlm_description IS NOT NULL
            ORDER BY created_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            return SearchResponse(query=request.query, results=[], total=0)

        descriptions = [row["vlm_description"] for row in rows]
        bm25_matcher.index_documents(descriptions)
        query_embedding = embedding_service.encode_text(request.query)

        bm25_results = bm25_matcher.search(request.query, top_k=len(descriptions))
        bm25_scores_dict = {idx: score for idx, score in bm25_results}
        max_bm25_score = max(bm25_scores_dict.values()) if bm25_scores_dict else 1.0

        results_with_scores = []
        for i, row in enumerate(rows):
            image_id = row["id"]
            bm25_score = bm25_scores_dict.get(i, 0.0)
            bm25_normalized = bm25_score / max_bm25_score if max_bm25_score > 0 else 0.0

            if bm25_normalized < config.MIN_BM25_SCORE:
                continue

            desc_embedding = embedding_service.encode_text(row["vlm_description"])
            clip_score = float(np.dot(query_embedding, desc_embedding))

            hybrid_score = config.BM25_WEIGHT * bm25_normalized + config.CLIP_WEIGHT * clip_score
            if hybrid_score >= config.DEEP_SEARCH_THRESHOLD:
                results_with_scores.append({"image_id": image_id, "score": hybrid_score})

        results_with_scores.sort(key=lambda x: x["score"], reverse=True)

        results = [
            SearchResult(
                image_id=item["image_id"],
                image_url=f"/images/{user_id}/{item['image_id']}.jpg",
                score=item["score"],
                global_score=item["score"],
                local_score=0.0,
            )
            for item in results_with_scores[:request.top_k]
        ]

        redis_cache.set_search_results(request.query, user_id, [r.model_dump() for r in results])
        return SearchResponse(query=request.query, results=results, total=len(results))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deep Search failed: {str(e)}")
