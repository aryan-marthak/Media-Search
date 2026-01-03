import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
THUMBNAILS_DIR = DATA_DIR / "thumbnails"

# Create directories
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/media_search"
)
DATABASE_URL_SYNC = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://postgres:postgres@localhost:5432/media_search"
)

# Qdrant
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_GRPC_PORT = int(os.getenv("QDRANT_GRPC_PORT", "6334"))

# JWT
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

# ML Models
SIGLIP_MODEL = os.getenv("SIGLIP_MODEL", "google/siglip-base-patch16-224")
VLM_MODEL = os.getenv("VLM_MODEL", "HuggingFaceTB/SmolVLM-Instruct")
DEVICE = os.getenv("DEVICE", "cuda")  # "cuda" for GPU, "cpu" for CPU

# Image settings
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
THUMBNAIL_SIZE = (300, 300)

# Search settings
NORMAL_SEARCH_TOP_K = 20
DEEP_SEARCH_CANDIDATE_K = 50
DEEP_SEARCH_FINAL_K = 20

# Vector dimensions
SIGLIP_EMBEDDING_DIM = 768
FACE_EMBEDDING_DIM = 512  # FaceNet/InceptionResnetV1 model
