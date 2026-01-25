"""
Query expansion service - maps user queries to related semantic terms.
Improves search recall by searching for synonyms and related concepts.
"""

from typing import List, Dict, Set
import json

# Semantic expansion mappings
QUERY_EXPANSIONS = {
    # Animals
    "dog": ["dog", "puppy", "canine", "pet", "animal", "pup"],
    "cat": ["cat", "kitten", "feline", "pet", "animal"],
    "bird": ["bird", "birds", "avian", "feather"],
    "horse": ["horse", "pony", "equine", "foal"],
    "person": ["person", "people", "human", "face", "portrait", "guy", "girl", "man", "woman"],
    "child": ["child", "kid", "children", "infant", "baby", "toddler"],
    "baby": ["baby", "infant", "newborn", "toddler"],
    
    # Locations
    "outdoor": ["outdoor", "nature", "outside", "exterior", "landscape", "scenery"],
    "indoor": ["indoor", "inside", "interior", "building", "room"],
    "mountain": ["mountain", "mountains", "peak", "alpine", "summit"],
    "beach": ["beach", "sand", "shore", "coast", "ocean"],
    "forest": ["forest", "woods", "woodland", "trees", "nature"],
    "city": ["city", "urban", "downtown", "street", "building"],
    "park": ["park", "garden", "outdoor", "nature"],
    
    # Nature/Weather
    "sunset": ["sunset", "dusk", "evening", "sunrise", "dawn", "golden hour"],
    "sunrise": ["sunrise", "dawn", "morning", "golden hour"],
    "rain": ["rain", "rainy", "wet", "weather", "storm"],
    "snow": ["snow", "snowy", "winter", "cold", "frost"],
    "cloud": ["cloud", "cloudy", "clouds", "sky", "overcast"],
    "sky": ["sky", "blue sky", "clouds", "weather", "atmosphere"],
    "water": ["water", "ocean", "sea", "lake", "river", "splash"],
    "tree": ["tree", "trees", "forest", "nature", "wood"],
    "flower": ["flower", "flowers", "bloom", "blossom", "floral"],
    
    # Objects/Food
    "food": ["food", "eating", "meal", "cuisine", "dish", "eat"],
    "drink": ["drink", "beverage", "coffee", "tea", "water"],
    "car": ["car", "vehicle", "automobile", "truck", "sedan"],
    "bike": ["bike", "bicycle", "motorcycle", "cycle"],
    "phone": ["phone", "mobile", "smartphone", "device"],
    "book": ["book", "reading", "literature", "novel", "text"],
    
    # Activities
    "running": ["running", "running", "jogging", "sprint", "active"],
    "walking": ["walking", "walk", "stroll", "hiking"],
    "jumping": ["jumping", "jump", "leap", "bounce"],
    "playing": ["playing", "play", "game", "sport", "recreation"],
    "swimming": ["swimming", "swim", "water", "pool", "beach"],
    "dancing": ["dancing", "dance", "movement", "performance"],
    "sleeping": ["sleeping", "sleep", "rest", "bed"],
    
    # Colors
    "blue": ["blue", "azure", "navy", "cyan", "turquoise"],
    "red": ["red", "crimson", "scarlet", "ruby", "pink"],
    "green": ["green", "lime", "forest", "emerald", "olive"],
    "yellow": ["yellow", "golden", "gold", "amber", "orange"],
    "black": ["black", "dark", "shadow", "noir"],
    "white": ["white", "light", "bright", "pale", "snow"],
    
    # Styles/Moods
    "happy": ["happy", "joyful", "smile", "joy", "cheerful"],
    "sad": ["sad", "unhappy", "melancholy", "tears", "sorrow"],
    "calm": ["calm", "peaceful", "serene", "quiet", "tranquil"],
    "busy": ["busy", "crowded", "hectic", "active", "chaos"],
    "dark": ["dark", "night", "shadow", "dim", "nighttime"],
    "bright": ["bright", "light", "sunny", "illuminated", "clear"],
    "cold": ["cold", "winter", "frost", "snow", "chill"],
    "hot": ["hot", "warm", "summer", "heat", "sunny"],
    
    # Quality
    "beautiful": ["beautiful", "pretty", "gorgeous", "stunning", "lovely"],
    "ugly": ["ugly", "unattractive", "unsightly", "poor"],
    "old": ["old", "ancient", "vintage", "historic", "aged"],
    "new": ["new", "modern", "fresh", "contemporary", "recent"],
    "clean": ["clean", "neat", "tidy", "organized", "spotless"],
    "dirty": ["dirty", "messy", "dusty", "grimy", "unclean"],
    
    # Composition
    "portrait": ["portrait", "headshot", "face", "person", "selfie"],
    "landscape": ["landscape", "wide", "scenery", "nature", "vista"],
    "close-up": ["close-up", "macro", "detail", "zoom", "magnified"],
    "wide": ["wide", "landscape", "broad", "expansive", "panoramic"],
    "black and white": ["black and white", "monochrome", "bw", "grayscale"],
}

# Lowercase version for case-insensitive lookup
QUERY_EXPANSIONS_LOWER = {k.lower(): v for k, v in QUERY_EXPANSIONS.items()}


def expand_query(query: str) -> List[str]:
    """
    Expand a query to include synonyms and related terms.
    
    Args:
        query: User's search query (single word or phrase)
        
    Returns:
        List of expanded query terms
    """
    query_lower = query.lower().strip()
    
    # Direct match
    if query_lower in QUERY_EXPANSIONS_LOWER:
        return QUERY_EXPANSIONS_LOWER[query_lower]
    
    # Check for partial matches (e.g., "dog" in "dog running")
    results = set()
    words = query_lower.split()
    
    for word in words:
        if word in QUERY_EXPANSIONS_LOWER:
            results.update(QUERY_EXPANSIONS_LOWER[word])
    
    # If we found expansions, return them
    if results:
        return list(results)
    
    # Fallback: return original query
    return [query_lower]


def expand_query_multi_word(query: str) -> List[str]:
    """
    Expand multi-word queries by expanding individual words and combining.
    
    For example: "dog in nature" -> ["dog", "puppy", ..., "outdoor", "nature", ...]
    
    Args:
        query: User's search query (can be multi-word)
        
    Returns:
        List of all expanded terms
    """
    query_lower = query.lower().strip()

    # Split into words
    words = query_lower.split()

    # Expand each word, preserving order and de-duplicating
    ordered: List[str] = []
    seen = set()

    for word in words:
        candidates = QUERY_EXPANSIONS_LOWER.get(word, [word])
        for term in candidates:
            term = term.strip().lower()
            if not term or term in seen:
                continue
            seen.add(term)
            ordered.append(term)

    return ordered


def get_primary_term(query: str) -> str:
    """
    Extract the primary searchable term from a query.
    
    For multi-word queries, returns the first recognized term.
    For single-word queries, returns the query itself.
    
    Args:
        query: User's search query
        
    Returns:
        The primary term (or original query if no match)
    """
    query_lower = query.lower().strip()
    
    # Try direct match first
    if query_lower in QUERY_EXPANSIONS_LOWER:
        return query_lower
    
    # Try individual words
    words = query_lower.split()
    for word in words:
        if word in QUERY_EXPANSIONS_LOWER:
            return word
    
    # Return original if no match found
    return query_lower


def get_query_context(query: str) -> Dict[str, any]:
    """
    Analyze query and return context information.
    
    Args:
        query: User's search query
        
    Returns:
        Dictionary with query context
    """
    query_lower = query.lower().strip()
    primary_term = get_primary_term(query)
    expansions = expand_query_multi_word(query)
    
    return {
        "original": query,
        "normalized": query_lower,
        "primary_term": primary_term,
        "expansions": expansions,
        "num_expansions": len(expansions),
        "is_recognized": primary_term in QUERY_EXPANSIONS_LOWER
    }


# Similarity-based term matching (for typos)
def find_similar_terms(query: str, threshold: float = 0.7) -> List[str]:
    """
    Find similar expansion terms even if not exact match (handles typos).
    
    Uses simple character overlap heuristic.
    
    Args:
        query: User's search query
        threshold: Similarity threshold (0-1)
        
    Returns:
        List of similar recognized terms
    """
    from difflib import SequenceMatcher
    
    query_lower = query.lower().strip()
    similar = []
    
    for term in QUERY_EXPANSIONS_LOWER.keys():
        ratio = SequenceMatcher(None, query_lower, term).ratio()
        if ratio >= threshold:
            similar.append(term)
    
    return similar


def create_query_variants(query: str) -> Dict[str, List[str]]:
    """
    Create different variants of a query for comprehensive search.
    
    Args:
        query: Original user query
        
    Returns:
        Dictionary with different query approaches
    """
    return {
        "direct": [query],
        "expanded": expand_query_multi_word(query),
        "primary_only": [get_primary_term(query)] if get_primary_term(query) in QUERY_EXPANSIONS_LOWER else [],
        "similar": find_similar_terms(query, threshold=0.6) if find_similar_terms(query) else []
    }


if __name__ == "__main__":
    # Test examples
    test_queries = [
        "dog",
        "dog running",
        "outdoor sunset",
        "person happy",
        "beautiful landscape",
        "black and white",
    ]
    
    print("Query Expansion Examples\n")
    print("=" * 80)
    
    for query in test_queries:
        context = get_query_context(query)
        print(f"\nQuery: '{query}'")
        print(f"  Normalized: {context['normalized']}")
        print(f"  Primary term: {context['primary_term']}")
        print(f"  Is recognized: {context['is_recognized']}")
        print(f"  Expansions ({context['num_expansions']} total):")
        for exp in context['expansions'][:5]:
            print(f"    - {exp}")
        if context['num_expansions'] > 5:
            print(f"    ... and {context['num_expansions'] - 5} more")
