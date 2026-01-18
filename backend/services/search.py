from typing import List, Dict, Any
from uuid import UUID
from PIL import Image

from services.embeddings import encode_text, calibrate_siglip_score
from services.qdrant import search_images
from services.query_parser import parse_query, get_query_importance
from services.metadata_matcher import compute_match_score, apply_relaxation
from services.storage import get_image_path
from services.query_expansion import expand_query_multi_word, get_primary_term
from config import NORMAL_SEARCH_TOP_K, DEEP_SEARCH_CANDIDATE_K, DEEP_SEARCH_FINAL_K


async def normal_search(
    query: str,
    user_id: str,
    top_k: int = NORMAL_SEARCH_TOP_K
) -> List[Dict[str, Any]]:
    """
    Fast embedding-based search with query expansion.
    Uses SigLIP text→image similarity and semantic query expansion.
    
    This is the default search mode optimized for speed and good recall.
    Automatically searches for query variations to improve hit rate.
    """
    # Step 1: Expand query to semantic variants
    expanded_terms = expand_query_multi_word(query)
    
    # Step 2: Search with each expanded term and aggregate results
    all_results = {}  # Using dict to deduplicate by ID
    
    for term in expanded_terms[:10]:  # Limit expansions to avoid slowdown
        term_embedding = encode_text(term)
        results = await search_images(user_id, term_embedding, min(top_k, 10))
        
        for r in results:
            image_id = r["id"]
            
            # Calibrate score
            calibrated_score = calibrate_siglip_score(r["score"])
            
            # Keep highest score for this image across all expansions
            if image_id not in all_results or calibrated_score > all_results[image_id]["score"]:
                all_results[image_id] = {
                    "id": image_id,
                    "metadata": r["metadata"],
                    "score": calibrated_score,
                    "raw_score": r["score"],
                    "matched_term": term
                }
    
    if not all_results:
        return []
    
    # Step 3: Sort by score and format results
    sorted_results = sorted(all_results.values(), key=lambda x: x["score"], reverse=True)
    
    return [
        {
            "id": UUID(r["id"]) if isinstance(r["id"], str) else r["id"],
            "filename": r["metadata"].get("filename", ""),
            "thumbnail_path": r["metadata"].get("thumbnail_path"),
            "score": r["score"],  # 0-1 confidence scale
            "matched_term": r.get("matched_term", query),
            "metadata": {
                k: v for k, v in r["metadata"].items() 
                if k not in ["image_id", "filename", "thumbnail_path"]
            }
        }
        for r in sorted_results[:top_k]
    ]


async def deep_search(
    query: str,
    user_id: str,
    top_k: int = DEEP_SEARCH_FINAL_K
) -> List[Dict[str, Any]]:
    """
    Accurate search with metadata matching and VLM validation.
    
    Pipeline:
    1. Vector recall: Get larger candidate pool via embeddings
    2. Parse query: Extract explicit attributes
    3. Soft metadata matching: Score candidates with fuzzy matching
    4. Controlled relaxation: If too few results, relax constraints
    5. Ranking: Sort by combined score
    6. (Optional) VLM validation: Validate top results
    
    This mode is slower but more precise for complex queries.
    """
    # Step 1: Vector recall with expanded candidate pool
    query_embedding = encode_text(query)
    candidates = await search_images(user_id, query_embedding, DEEP_SEARCH_CANDIDATE_K)
    
    if not candidates:
        return []
    
    # Step 2: Parse query attributes
    query_attrs = parse_query(query)
    weights = get_query_importance(query_attrs)
    
    # Step 3: Score candidates with metadata matching
    scored_candidates = []
    for candidate in candidates:
        metadata = candidate["metadata"]
        
        # Compute metadata match score
        meta_score = compute_match_score(query_attrs, metadata, weights)
        
        # Calibrate raw embedding score and combine with metadata score
        # Embedding score is calibrated from cosine similarity to 0-1 confidence
        raw_embedding_score = candidate["score"]
        embedding_score = calibrate_siglip_score(raw_embedding_score)
        combined_score = (0.6 * embedding_score) + (0.4 * meta_score)
        
        scored_candidates.append({
            "id": candidate["id"],
            "metadata": metadata,
            "embedding_score": embedding_score,
            "meta_score": meta_score,
            "combined_score": combined_score
        })
    
    # Step 4: Check if we have enough good results, otherwise apply relaxation
    good_results = [c for c in scored_candidates if c["combined_score"] > 0.5]
    
    if len(good_results) < top_k:
        # Apply relaxation levels progressively
        for level in range(1, 4):
            relaxed_attrs = apply_relaxation(query_attrs, level)
            
            for candidate in scored_candidates:
                new_meta_score = compute_match_score(relaxed_attrs, candidate["metadata"], weights)
                # Only update if it improves the score
                if new_meta_score > candidate["meta_score"]:
                    candidate["meta_score"] = new_meta_score
                    candidate["combined_score"] = (0.6 * candidate["embedding_score"]) + (0.4 * new_meta_score)
            
            good_results = [c for c in scored_candidates if c["combined_score"] > 0.5]
            if len(good_results) >= top_k:
                break
    
    # Step 5: Sort by combined score and take top_k
    scored_candidates.sort(key=lambda x: x["combined_score"], reverse=True)
    top_results = scored_candidates[:top_k]
    
    # Step 6: Optional VLM validation for top results
    # Commented out for performance - enable for highest accuracy
    # validated_results = await vlm_validate_results(query, top_results[:10])
    
    # Format results
    return [
        {
            "id": UUID(r["id"]) if isinstance(r["id"], str) else r["id"],
            "filename": r["metadata"].get("filename", ""),
            "thumbnail_path": r["metadata"].get("thumbnail_path"),
            "score": r["combined_score"],
            "metadata": {
                k: v for k, v in r["metadata"].items() 
                if k not in ["image_id", "filename", "thumbnail_path"]
            }
        }
        for r in top_results
    ]


async def vlm_validate_results(
    query: str,
    candidates: List[Dict],
    db_session=None
) -> List[Dict]:
    """
    Use VLM to validate top candidates against the query.
    This is expensive but provides highest accuracy.
    """
    from services.vlm import validate_image_for_query
    
    validated = []
    
    for candidate in candidates:
        try:
            # Load image
            # Note: This requires database access to get file path
            # For now, we skip VLM validation in favor of metadata matching
            matches, confidence, reason = True, 0.8, ""  # Placeholder
            
            if matches:
                candidate["vlm_confidence"] = confidence
                candidate["vlm_reason"] = reason
                validated.append(candidate)
        except Exception:
            # If VLM fails, keep the candidate based on embedding/metadata score
            validated.append(candidate)
    
    return validated
