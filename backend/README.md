# Media Search Backend

AI-powered image search using CLIP (Contrastive Language-Image Pre-training) embeddings with advanced features like local re-ranking, spell checking, and diversity filtering.

## Features

- 🔍 **Semantic Search**: Search images using natural language queries
- 🎯 **Local Re-ranking**: Enhanced accuracy with crop-based scoring
- ✨ **Spell Checking**: Automatic query correction and suggestions
- 🎨 **Diversity Filtering**: Prevents similar images from dominating results
- ⚡ **Redis Caching**: Fast embedding retrieval
- 🗄️ **PostgreSQL + Qdrant**: Robust metadata and vector storage

## Architecture

```
┌─────────────┐
│   FastAPI   │  API Server
└──────┬──────┘
       │
       ├─────► PostgreSQL (Metadata)
       ├─────► Qdrant (Vector DB)
       ├─────► Redis (Cache)
       └─────► CLIP Model (ViT-L-14)
```

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL
- Qdrant
- Redis

### Installation

1. **Create virtual environment and install dependencies:**
   ```bash
   setup_venv.bat
   ```

2. **Configure environment variables (optional):**
   ```bash
   copy .env.example .env
   # Edit .env with your settings
   ```

3. **Run the backend:**
   ```bash
   run_backend.bat
   ```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check
```
GET /
```

### Upload Image
```
POST /upload
Content-Type: multipart/form-data
Body: file (image file)
```

### Search Images
```
POST /search
Content-Type: application/json
Body: {
  "query": "sunset over mountains",
  "top_k": 10
}
```

### Get Gallery
```
GET /gallery
```

### Delete Images
```
DELETE /images
Content-Type: application/json
Body: ["image-id-1", "image-id-2"]
```

### Spell Check
```
POST /spell-check
Content-Type: application/json
Body: {
  "query": "sunst"
}
```

### Search Suggestions
```
GET /search-suggestions?query=sun
```

## Configuration

Edit `config.py` or set environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | localhost | PostgreSQL host |
| `POSTGRES_PORT` | 5432 | PostgreSQL port |
| `QDRANT_HOST` | localhost | Qdrant host |
| `QDRANT_PORT` | 6333 | Qdrant port |
| `REDIS_HOST` | localhost | Redis host |
| `REDIS_PORT` | 6379 | Redis port |
| `CLIP_MODEL` | ViT-L-14 | CLIP model architecture |
| `DEVICE` | cpu | Device for inference (cpu/cuda) |

## Utilities

### Reindex All Images
```bash
venv\Scripts\activate.bat
python reindex.py
```

## Project Structure

```
backend/
├── main.py              # FastAPI application
├── config.py            # Configuration
├── models.py            # Pydantic models
├── database.py          # Database connections
├── embedding_service.py # CLIP service
├── redis_cache.py       # Redis cache
├── search_helper.py     # Spell checking
├── reindex.py           # Reindex utility
├── requirements.txt     # Dependencies
├── setup_venv.bat       # Setup script
├── run_backend.bat      # Run script
└── .env.example         # Environment template
```

## Troubleshooting

### CLIP Model Not Loading
- Ensure you have enough RAM (model requires ~2GB)
- Check internet connection for first-time download

### Database Connection Errors
- Verify PostgreSQL/Qdrant/Redis are running
- Check connection settings in `.env` or `config.py`

### Slow Search Performance
- Enable Redis caching (default: enabled)
- Consider using GPU (`DEVICE=cuda`)
- Reduce `NUM_CROPS` for faster local re-ranking

## License

MIT
