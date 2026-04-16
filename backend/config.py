"""
Configuration module for Media Search Backend.
Loads settings from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
STORAGE_DIR = BASE_DIR / "storage" / "images"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# PostgreSQL Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "media_search")
POSTGRES_USER = os.getenv("POSTGRES_USER", "user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Qdrant Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = "clip_embeddings"

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# CLIP Model Configuration
CLIP_MODEL = os.getenv("CLIP_MODEL", "ViT-L-14")
CLIP_PRETRAINED = os.getenv("CLIP_PRETRAINED", "openai")

# Auto-detect device: use GPU if available, otherwise CPU
import torch
DEVICE = os.getenv("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")

# Search Configuration
TOP_K = 20
SCORE_THRESHOLD = 0.20
DEEP_SEARCH_THRESHOLD = 0.35
ENABLE_LOCAL_RERANKING = True
ENABLE_ZERO_SHOT_FILTER = False
ZERO_SHOT_THRESHOLD = 0.55
GLOBAL_WEIGHT = 0.6
LOCAL_WEIGHT = 0.4
NUM_CROPS = 5

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# VLM Configuration
ENABLE_VLM = os.getenv("ENABLE_VLM", "true").lower() == "true"

# Deep Search Hybrid Configuration
BM25_WEIGHT = 0.7
CLIP_WEIGHT = 0.3
MIN_BM25_SCORE = 0.30

# JWT Authentication
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production-use-a-long-random-string")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30
