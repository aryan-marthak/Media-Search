"""
BM25 Text Matching Service for Deep Search.
Provides keyword-based matching for VLM descriptions.
"""
from typing import List, Dict, Tuple
import math
import re
from collections import Counter

class BM25Matcher:
    """BM25 algorithm for ranking text documents by relevance to a query."""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 matcher.
        
        Args:
            k1: Term frequency saturation parameter (default: 1.5)
            b: Length normalization parameter (default: 0.75)
        """
        self.k1 = k1
        self.b = b
        self.documents = []
        self.doc_lengths = []
        self.avg_doc_length = 0
        self.doc_freqs = {}
        self.idf = {}
        self.doc_count = 0
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase words."""
        # Remove special characters and convert to lowercase
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        # Split and filter empty strings
        tokens = [word for word in text.split() if word]
        return tokens
    
    def index_documents(self, documents: List[str]):
        """
        Index documents for BM25 scoring.
        
        Args:
            documents: List of document strings (VLM descriptions)
        """
        self.documents = documents
        self.doc_count = len(documents)
        
        # Tokenize all documents
        tokenized_docs = [self.tokenize(doc) for doc in documents]
        
        # Calculate document lengths
        self.doc_lengths = [len(doc) for doc in tokenized_docs]
        self.avg_doc_length = sum(self.doc_lengths) / self.doc_count if self.doc_count > 0 else 0
        
        # Calculate document frequencies
        self.doc_freqs = {}
        for doc_tokens in tokenized_docs:
            unique_tokens = set(doc_tokens)
            for token in unique_tokens:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1
        
        # Calculate IDF (Inverse Document Frequency)
        self.idf = {}
        for token, freq in self.doc_freqs.items():
            # IDF formula: log((N - df + 0.5) / (df + 0.5) + 1)
            self.idf[token] = math.log((self.doc_count - freq + 0.5) / (freq + 0.5) + 1)
    
    def score_document(self, query: str, doc_index: int) -> float:
        """
        Calculate BM25 score for a document given a query.
        
        Args:
            query: Search query string
            doc_index: Index of document to score
            
        Returns:
            BM25 score (higher is better)
        """
        if doc_index >= len(self.documents):
            return 0.0
        
        query_tokens = self.tokenize(query)
        doc_tokens = self.tokenize(self.documents[doc_index])
        doc_length = self.doc_lengths[doc_index]
        
        # Count term frequencies in document
        term_freqs = Counter(doc_tokens)
        
        score = 0.0
        for token in query_tokens:
            if token not in self.idf:
                continue
            
            # Term frequency in document
            tf = term_freqs.get(token, 0)
            
            # BM25 formula
            # score += IDF * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_length / avg_doc_length)))
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length))
            score += self.idf[token] * (numerator / denominator)
        
        return score
    
    def search(self, query: str, top_k: int = 20) -> List[Tuple[int, float]]:
        """
        Search documents and return top-k results.
        
        Args:
            query: Search query string
            top_k: Number of top results to return
            
        Returns:
            List of (doc_index, score) tuples, sorted by score descending
        """
        scores = []
        for i in range(len(self.documents)):
            score = self.score_document(query, i)
            if score > 0:  # Only include documents with non-zero scores
                scores.append((i, score))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:top_k]


# Singleton instance
_bm25_matcher = None

def get_bm25_matcher() -> BM25Matcher:
    """Get or create BM25 matcher singleton."""
    global _bm25_matcher
    if _bm25_matcher is None:
        _bm25_matcher = BM25Matcher()
    return _bm25_matcher
