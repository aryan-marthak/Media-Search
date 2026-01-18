from typing import Dict, List, Optional
from services.vocabulary import (
    normalize_object, 
    get_object_hierarchy,
    get_action_similarity,
    OBJECT_SYNONYMS
)


def compute_match_score(
    query_attrs: Dict,
    image_metadata: Dict,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Compute a soft match score between query attributes and image metadata.
    Uses semantic proximity, not exact matching.
    
    Score breakdown:
    - 1.0: Exact match
    - 0.8: Near match (e.g., walking ≈ slow walking)
    - 0.6: Category match (e.g., man → person)
    - 0.0: No match
    
    Returns aggregate score between 0 and 1.
    """
    if weights is None:
        weights = {
            "objects": 0.3,
            "action": 0.3,
            "time": 0.2,
            "scene": 0.1,
            "weather": 0.05,
            "emotion": 0.05
        }
    
    total_score = 0.0
    total_weight = 0.0
    
    # Object matching
    if query_attrs.get("objects"):
        obj_score = match_objects(query_attrs["objects"], image_metadata.get("objects", []))
        total_score += obj_score * weights["objects"]
        total_weight += weights["objects"]
    
    # Action matching
    if query_attrs.get("action"):
        action_score = get_action_similarity(
            query_attrs["action"],
            image_metadata.get("action")
        )
        total_score += action_score * weights["action"]
        total_weight += weights["action"]
    
    # Time matching
    if query_attrs.get("time"):
        time_score = match_time(query_attrs["time"], image_metadata.get("time"))
        total_score += time_score * weights["time"]
        total_weight += weights["time"]
    
    # Scene matching
    if query_attrs.get("scene"):
        scene_score = match_exact_or_zero(query_attrs["scene"], image_metadata.get("scene"))
        total_score += scene_score * weights["scene"]
        total_weight += weights["scene"]
    
    # Weather matching  
    if query_attrs.get("weather"):
        weather_score = match_exact_or_zero(query_attrs["weather"], image_metadata.get("weather"))
        total_score += weather_score * weights["weather"]
        total_weight += weights["weather"]
    
    # Emotion matching
    if query_attrs.get("emotion"):
        emotion_score = match_exact_or_zero(query_attrs["emotion"], image_metadata.get("emotion"))
        total_score += emotion_score * weights["emotion"]
        total_weight += weights["emotion"]
    
    if total_weight == 0:
        return 0.0
    
    return total_score / total_weight


def match_objects(query_objects: List[str], image_objects: List[str]) -> float:
    """
    Match objects with hierarchy-aware scoring.
    Allows relaxation: man → person scores 0.6
    """
    if not query_objects or not image_objects:
        return 0.0
    
    # Normalize all objects
    query_normalized = [normalize_object(o) for o in query_objects]
    image_normalized = [normalize_object(o) for o in image_objects]
    
    best_score = 0.0
    
    for q_obj in query_normalized:
        # Get hierarchy for query object
        q_hierarchy = get_object_hierarchy(q_obj)
        
        for i_obj in image_normalized:
            i_hierarchy = get_object_hierarchy(i_obj)
            
            # Exact match
            if q_obj == i_obj:
                best_score = max(best_score, 1.0)
            # Query is more specific than image (man vs person)
            elif len(q_hierarchy) > 1 and q_hierarchy[1] in i_hierarchy:
                best_score = max(best_score, 0.8)
            # Image is more specific than query
            elif len(i_hierarchy) > 1 and i_hierarchy[1] in q_hierarchy:
                best_score = max(best_score, 0.9)
            # Same category
            elif q_hierarchy[-1] == i_hierarchy[-1]:
                best_score = max(best_score, 0.6)
    
    return best_score


def match_time(query_time: str, image_time: Optional[str]) -> float:
    """Match time of day with fuzzy matching."""
    if not image_time:
        return 0.0
    
    q = query_time.lower()
    i = image_time.lower()
    
    if q == i:
        return 1.0
    
    # Group similar times
    night_variants = ["night", "nighttime", "dark", "evening", "midnight"]
    day_variants = ["day", "daytime", "afternoon", "bright", "midday"]
    
    if q in night_variants and i in night_variants:
        return 0.9
    if q in day_variants and i in day_variants:
        return 0.9
    
    return 0.0


def match_exact_or_zero(query_val: str, image_val: Optional[str]) -> float:
    """Simple exact match or zero."""
    if not image_val:
        return 0.0
    return 1.0 if query_val.lower() == image_val.lower() else 0.0


def apply_relaxation(query_attrs: Dict, level: int = 0) -> Dict:
    """
    Apply controlled relaxation to query attributes.
    
    Level 0: No relaxation (exact query)
    Level 1: Relax object specificity (man → person)
    Level 2: Relax scene
    Level 3: Relax weather/emotion
    
    Never relaxes: action and time (core intent)
    """
    relaxed = query_attrs.copy()
    
    if level >= 1:
        # Relax objects to their categories
        if relaxed.get("objects"):
            new_objects = []
            for obj in relaxed["objects"]:
                normalized = normalize_object(obj)
                # Check if it belongs to a category
                for category, members in OBJECT_SYNONYMS.items():
                    if normalized in members:
                        new_objects.append(category)
                        break
                else:
                    new_objects.append(normalized)
            relaxed["objects"] = new_objects
    
    if level >= 2:
        # Remove scene constraint
        relaxed["scene"] = None
    
    if level >= 3:
        # Remove weather and emotion constraints
        relaxed["weather"] = None
        relaxed["emotion"] = None
    
    return relaxed
