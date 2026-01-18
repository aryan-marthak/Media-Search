"""
Database initialization and connection management.
Handles PostgreSQL and Qdrant vector database.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import config


def get_db_connection():
    """Create a new PostgreSQL database connection."""
    return psycopg2.connect(config.DATABASE_URL, cursor_factory=RealDictCursor)


def init_postgres():
    """Initialize PostgreSQL schema."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id UUID PRIMARY KEY,
            file_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print(">> PostgreSQL initialized")


# Qdrant client singleton
_qdrant_client = None


def get_qdrant_client():
    """Get or create Qdrant client singleton."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
    return _qdrant_client


def init_qdrant(vector_size=768):
    """
    Initialize Qdrant collection for CLIP embeddings.
    Vector size: 768 dimensions (ViT-L-14)
    """
    client = get_qdrant_client()
    
    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [col.name for col in collections]
    
    if config.QDRANT_COLLECTION not in collection_names:
        client.create_collection(
            collection_name=config.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
        print(f">> Qdrant collection '{config.QDRANT_COLLECTION}' created (768-dim)")
    else:
        print(f">> Qdrant collection '{config.QDRANT_COLLECTION}' already exists")


def init_databases():
    """Initialize both PostgreSQL and Qdrant databases."""
    init_postgres()
    init_qdrant()
