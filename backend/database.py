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
    """Initialize PostgreSQL schema (clean slate — drops and recreates all tables)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Drop existing tables in reverse dependency order
    cursor.execute("DROP TABLE IF EXISTS faces CASCADE")
    cursor.execute("DROP TABLE IF EXISTS face_clusters CASCADE")
    cursor.execute("DROP TABLE IF EXISTS images CASCADE")
    cursor.execute("DROP TABLE IF EXISTS users CASCADE")

    # Users table
    cursor.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Images — scoped to a user
    cursor.execute("""
        CREATE TABLE images (
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
        CREATE TABLE face_clusters (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT,
            representative_face_id UUID,
            face_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Faces — linked to images (cascades user_id via images)
    cursor.execute("""
        CREATE TABLE faces (
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
    print(">> PostgreSQL schema initialized (clean slate with user_id columns)")


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
    Recreates the collection on startup to match the clean slate approach.
    Vector size: 768 dimensions (ViT-L-14)
    """
    client = get_qdrant_client()

    # Delete and recreate for clean slate
    collections = client.get_collections().collections
    collection_names = [col.name for col in collections]

    if config.QDRANT_COLLECTION in collection_names:
        client.delete_collection(config.QDRANT_COLLECTION)
        print(f">> Qdrant collection '{config.QDRANT_COLLECTION}' dropped (clean slate)")

    client.create_collection(
        collection_name=config.QDRANT_COLLECTION,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    print(f">> Qdrant collection '{config.QDRANT_COLLECTION}' created (768-dim)")


def init_databases():
    """Initialize both PostgreSQL and Qdrant databases."""
    init_postgres()
    init_qdrant()
