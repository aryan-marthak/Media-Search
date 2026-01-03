from typing import Dict, List, Optional
import re

# Vocabulary mappings for normalization
OBJECT_SYNONYMS = {
    "person": ["man", "woman", "boy", "girl", "child", "human", "people", "guy", "lady", "kid"],
    "vehicle": ["car", "truck", "bus", "motorcycle", "bike", "automobile", "van"],
    "animal": ["dog", "cat", "bird", "horse", "cow", "pet"],
    "building": ["house", "apartment", "skyscraper", "office", "store", "shop"],
}

ACTION_SYNONYMS = {
    "walking": ["walk", "strolling", "slow walking", "ambling"],
    "running": ["run", "jogging", "sprinting", "dashing"],
    "sitting": ["sit", "seated", "resting"],
    "standing": ["stand", "upright", "waiting"],
    "eating": ["eat", "dining", "having food"],
    "talking": ["talk", "speaking", "chatting", "conversing"],
}

TIME_SYNONYMS = {
    "day": ["daytime", "afternoon", "midday", "bright"],
    "night": ["nighttime", "dark", "evening", "midnight"],
    "sunset": ["dusk", "twilight", "golden hour"],
    "dawn": ["sunrise", "early morning", "daybreak"],
}

SCENE_SYNONYMS = {
    "street": ["road", "sidewalk", "pavement", "avenue"],
    "indoor": ["inside", "interior", "room", "indoors"],
    "outdoor": ["outside", "exterior", "outdoors"],
    "beach": ["shore", "seaside", "coast"],
    "park": ["garden", "green space", "lawn"],
    "city": ["urban", "downtown", "metropolitan"],
}


def normalize_object(obj: str) -> str:
    """Normalize an object name to canonical form."""
    obj_lower = obj.lower().strip()
    
    for canonical, synonyms in OBJECT_SYNONYMS.items():
        if obj_lower == canonical or obj_lower in synonyms:
            return canonical
    
    return obj_lower


def normalize_action(action: str) -> Optional[str]:
    """Normalize an action to canonical form."""
    if not action:
        return None
    
    action_lower = action.lower().strip()
    
    for canonical, synonyms in ACTION_SYNONYMS.items():
        if action_lower == canonical or action_lower in synonyms:
            return canonical
    
    return action_lower


def normalize_time(time: str) -> Optional[str]:
    """Normalize time of day to canonical form."""
    if not time:
        return None
    
    time_lower = time.lower().strip()
    
    for canonical, synonyms in TIME_SYNONYMS.items():
        if time_lower == canonical or time_lower in synonyms:
            return canonical
    
    return time_lower


def normalize_scene(scene: str) -> Optional[str]:
    """Normalize scene type to canonical form."""
    if not scene:
        return None
    
    scene_lower = scene.lower().strip()
    
    for canonical, synonyms in SCENE_SYNONYMS.items():
        if scene_lower == canonical or scene_lower in synonyms:
            return canonical
    
    return scene_lower


def normalize_metadata(metadata: Dict) -> Dict:
    """Normalize all metadata fields to canonical vocabulary."""
    normalized = {
        "objects": [],
        "action": None,
        "time": None,
        "scene": None,
        "weather": metadata.get("weather"),
        "emotion": metadata.get("emotion"),
        "caption": metadata.get("caption")
    }
    
    # Normalize objects
    if metadata.get("objects"):
        normalized["objects"] = [normalize_object(obj) for obj in metadata["objects"]]
    
    # Normalize action
    normalized["action"] = normalize_action(metadata.get("action"))
    
    # Normalize time
    normalized["time"] = normalize_time(metadata.get("time"))
    
    # Normalize scene
    normalized["scene"] = normalize_scene(metadata.get("scene"))
    
    return normalized


def get_object_hierarchy(obj: str) -> List[str]:
    """Get hierarchy of object categories (specific → general)."""
    obj_lower = obj.lower()
    
    # Check if it's a specific type of a category
    for category, members in OBJECT_SYNONYMS.items():
        if obj_lower in members:
            return [obj_lower, category]
    
    # Check if it's already a category
    if obj_lower in OBJECT_SYNONYMS:
        return [obj_lower]
    
    return [obj_lower]


def get_action_similarity(action1: Optional[str], action2: Optional[str]) -> float:
    """
    Compute similarity between two actions.
    1.0 = exact match
    0.8 = same category
    0.0 = different
    """
    if not action1 or not action2:
        return 0.0
    
    a1 = action1.lower().strip()
    a2 = action2.lower().strip()
    
    if a1 == a2:
        return 1.0
    
    # Check if they're in the same category
    for canonical, synonyms in ACTION_SYNONYMS.items():
        a1_match = a1 == canonical or a1 in synonyms
        a2_match = a2 == canonical or a2 in synonyms
        if a1_match and a2_match:
            return 0.8
    
    return 0.0
