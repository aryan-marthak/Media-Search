"""
Search helper utilities for spell checking and suggestions.
"""
from spellchecker import SpellChecker
from typing import List, Optional


class SearchHelper:
    """Search enhancement utilities."""
    
    def __init__(self):
        """Initialize spell checker."""
        self.spell = SpellChecker()
        
        # Common search terms for suggestions
        self.common_terms = [
            "sunset", "sunrise", "ocean", "beach", "mountain", "landscape",
            "car", "vehicle", "bike", "motorcycle",
            "people", "person", "group", "friends", "family",
            "building", "palace", "fort", "temple", "monument",
            "nature", "tree", "forest", "sky", "water",
            "city", "street", "road", "bridge", "architecture",
            "food", "animal", "dog", "cat", "bird",
            "flower", "garden", "park", "river", "lake"
        ]
    
    def correct_spelling(self, query: str) -> tuple[str, bool]:
        """
        Check and correct spelling in query.
        
        Args:
            query: Search query
            
        Returns:
            (corrected_query, was_corrected)
        """
        words = query.lower().split()
        corrected_words = []
        was_corrected = False
        
        for word in words:
            # Get correction
            corrected = self.spell.correction(word)
            
            if corrected and corrected != word:
                corrected_words.append(corrected)
                was_corrected = True
            else:
                corrected_words.append(word)
        
        corrected_query = " ".join(corrected_words)
        return corrected_query, was_corrected
    
    def get_suggestions(self, query: str, max_suggestions: int = 3) -> List[str]:
        """
        Get alternative search suggestions based on query.
        
        Args:
            query: Search query
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of suggested search terms
        """
        query_lower = query.lower()
        suggestions = []
        
        # Find similar terms from common terms
        for term in self.common_terms:
            if term not in query_lower and len(suggestions) < max_suggestions:
                # Simple similarity check
                if any(word in term for word in query_lower.split()):
                    suggestions.append(term)
        
        # If no similar terms, return popular terms
        if not suggestions:
            suggestions = self.common_terms[:max_suggestions]
        
        return suggestions[:max_suggestions]
    
    def get_did_you_mean(self, query: str) -> Optional[str]:
        """
        Get "did you mean" suggestion for misspelled query.
        
        Args:
            query: Search query
            
        Returns:
            Suggested correction or None
        """
        words = query.lower().split()
        
        for word in words:
            # Check if word is misspelled
            if word not in self.spell:
                # Get best candidate
                candidates = self.spell.candidates(word)
                if candidates:
                    best_match = list(candidates)[0]
                    if best_match != word:
                        return query.replace(word, best_match)
        
        return None


# Global singleton instance
_search_helper = None


def get_search_helper() -> SearchHelper:
    """Get or create search helper singleton."""
    global _search_helper
    if _search_helper is None:
        _search_helper = SearchHelper()
    return _search_helper
