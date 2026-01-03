from typing import Dict, List, Optional
import re

from services.vocabulary import OBJECT_SYNONYMS, ACTION_SYNONYMS, TIME_SYNONYMS, SCENE_SYNONYMS


def parse_query(query: str) -> Dict[str, any]:
    """
    Parse a natural language query to extract explicit attributes.
    Only extracts what the user explicitly mentions - does not infer missing attributes.
    
    Example:
        "man walking at night" → {"object": "man", "action": "walking", "time": "night"}
        "happy dog" → {"object": "dog", "emotion": "happy"}
    """
    query_lower = query.lower().strip()
    tokens = query_lower.split()
    
    result = {
        "objects": [],
        "action": None,
        "time": None,
        "scene": None,
        "weather": None,
        "emotion": None,
        "raw_query": query
    }
    
    # Extract objects
    all_objects = set()
    for category, synonyms in OBJECT_SYNONYMS.items():
        all_objects.add(category)
        all_objects.update(synonyms)
    
    for token in tokens:
        if token in all_objects:
            result["objects"].append(token)
    
    # Also check multi-word patterns
    person_patterns = ["young man", "old man", "young woman", "old woman", "little boy", "little girl"]
    for pattern in person_patterns:
        if pattern in query_lower:
            # Extract the specific term
            result["objects"].append(pattern.split()[-1])  # e.g., "man", "woman"
    
    # Extract action
    all_actions = set()
    for canonical, synonyms in ACTION_SYNONYMS.items():
        all_actions.add(canonical)
        all_actions.update(synonyms)
    
    for token in tokens:
        if token in all_actions:
            result["action"] = token
            break
    
    # Check for -ing forms that might be actions
    for token in tokens:
        if token.endswith("ing") and token not in all_actions:
            # Could be an action verb
            result["action"] = token
            break
    
    # Extract time
    all_times = set()
    for canonical, synonyms in TIME_SYNONYMS.items():
        all_times.add(canonical)
        all_times.update(synonyms)
    
    for token in tokens:
        if token in all_times:
            result["time"] = token
            break
    
    # Check for time phrases
    if "at night" in query_lower or "during night" in query_lower:
        result["time"] = "night"
    elif "at day" in query_lower or "during day" in query_lower or "daytime" in query_lower:
        result["time"] = "day"
    
    # Extract scene
    all_scenes = set()
    for canonical, synonyms in SCENE_SYNONYMS.items():
        all_scenes.add(canonical)
        all_scenes.update(synonyms)
    
    for token in tokens:
        if token in all_scenes:
            result["scene"] = token
            break
    
    # Check for scene phrases
    if "on the street" in query_lower or "on street" in query_lower:
        result["scene"] = "street"
    elif "at the beach" in query_lower or "on beach" in query_lower:
        result["scene"] = "beach"
    elif "in the park" in query_lower or "at park" in query_lower:
        result["scene"] = "park"
    
    # Extract weather
    weather_terms = ["sunny", "rainy", "cloudy", "snowy", "foggy", "stormy", "clear"]
    for term in weather_terms:
        if term in query_lower:
            result["weather"] = term
            break
    
    # Extract emotion
    emotion_terms = ["happy", "sad", "angry", "surprised", "scared", "smiling", "laughing", "crying"]
    for term in emotion_terms:
        if term in query_lower:
            result["emotion"] = term
            break
    
    return result


def get_query_importance(parsed: Dict) -> Dict[str, float]:
    """
    Determine importance weights for each attribute based on query structure.
    Core intent (action + time) should not be relaxed.
    """
    weights = {
        "objects": 0.7,  # Can be relaxed (man → person)
        "action": 1.0,   # Core intent - never relax
        "time": 0.9,     # Usually important context
        "scene": 0.6,    # Can be relaxed
        "weather": 0.4,  # Often supplementary
        "emotion": 0.5   # Often supplementary
    }
    
    return weights
