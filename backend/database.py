"""
Database initialization and connection management.
Handles PostgreSQL and Qdrant vector database.

Option A — clean slate migration:
All tables are dropped and recreated with user_id columns.
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
    """Initialize PostgreSQL schema using CREATE TABLE IF NOT EXISTS — data is preserved across restarts."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Images — scoped to a user
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            file_path TEXT NOT NULL,
            vlm_description TEXT,
            vlm_processed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Face clusters — scoped to a user
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS face_clusters (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT,
            representative_face_id UUID,
            face_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Faces — linked to images
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faces (
            id UUID PRIMARY KEY,
            image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
            cluster_id UUID REFERENCES face_clusters(id) ON DELETE SET NULL,
            face_embedding FLOAT8[] NOT NULL,
            bbox_x INTEGER,
            bbox_y INTEGER,
            bbox_width INTEGER,
            bbox_height INTEGER,
            confidence FLOAT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print(">> PostgreSQL schema ready (tables created if not exists)")


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
    Only creates the collection if it doesn't already exist — data is preserved.
    Vector size: 768 dimensions (ViT-L-14)
    """
    client = get_qdrant_client()

    collections = client.get_collections().collections
    collection_names = [col.name for col in collections]

    if config.QDRANT_COLLECTION not in collection_names:
        client.create_collection(
            collection_name=config.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        print(f">> Qdrant collection '{config.QDRANT_COLLECTION}' created (768-dim)")
    else:
        print(f">> Qdrant collection '{config.QDRANT_COLLECTION}' already exists — keeping data")


def init_databases():
    """Initialize both PostgreSQL and Qdrant databases."""
    init_postgres()
    init_qdrant()
