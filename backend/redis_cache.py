"""
Redis cache service for storing image embeddings.
Provides fast access to frequently used embeddings.
"""
import redis
import numpy as np
import pickle
from typing import Optional
import config


class RedisCache:
    """Redis cache for image embeddings."""
    
    def __init__(self):
        """Initialize Redis connection."""
        self.client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=0,
            decode_responses=False  # Store binary data
        )
        print(f">> Redis connected: {config.REDIS_HOST}:{config.REDIS_PORT}")
    
    def get_embedding(self, image_id: str) -> Optional[np.ndarray]:
        """
        Get cached embedding for an image.
        
        Args:
            image_id: UUID of the image
            
        Returns:
            numpy array of embedding or None if not cached
        """
        key = f"emb:{image_id}"
        data = self.client.get(key)
        
        if data is None:
            return None
        
        # Deserialize numpy array
        embedding = pickle.loads(data)
        return embedding
    
    def set_embedding(self, image_id: str, embedding: np.ndarray, ttl: int = None):
        """
        Cache an embedding for an image.
        
        Args:
            image_id: UUID of the image
            embedding: numpy array of embedding
            ttl: Time to live in seconds (None = no expiration)
        """
        key = f"emb:{image_id}"
        data = pickle.dumps(embedding)
        
        if ttl:
            self.client.setex(key, ttl, data)
        else:
            self.client.set(key, data)
    
    def delete_embedding(self, image_id: str):
        """Delete cached embedding for an image."""
        key = f"emb:{image_id}"
        self.client.delete(key)
    
    def clear_all(self):
        """Clear all cached embeddings."""
        self.client.flushdb()
        print(">> Redis cache cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        info = self.client.info('stats')
        memory = self.client.info('memory')
        
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses
        hit_rate = round((hits / total) * 100, 2) if total > 0 else 0.0
        
        return {
            'total_keys': self.client.dbsize(),
            'used_memory_mb': round(memory['used_memory'] / 1024 / 1024, 2),
            'hits': hits,
            'misses': misses,
            'hit_rate': hit_rate
        }


# Global singleton instance
_redis_cache = None


def get_redis_cache() -> RedisCache:
    """Get or create Redis cache singleton."""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache
