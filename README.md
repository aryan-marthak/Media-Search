# Media Search System

A powerful image search system using **SigLIP embeddings** (global + local), **Qdrant** vector database, **PostgreSQL** metadata storage, and a modern **React** frontend.

## 🎯 Features

- **Two-Stage Search**: Global recall + local crop re-ranking for superior accuracy
- **SigLIP Embeddings**: State-of-the-art vision-language model
- **Local Storage**: Images stored on disk (easily migrated to cloud)
- **Modern UI**: Premium dark mode with glassmorphism and smooth animations
- **Drag & Drop**: Easy image upload interface

## 🏗️ Architecture

### Search Algorithm

1. **Global Recall** (Fast)
   - Query → SigLIP text encoder
   - Search Qdrant for Top-50 candidates using global embeddings
   
2. **Local Re-ranking** (Accurate)
   - For each candidate, generate 5 crops (1 center + 4 grid)
   - Compute SigLIP embeddings for each crop
   - Find max similarity across crops
   
3. **Final Score**
   ```
   final_score = 0.7 × global_similarity + 0.3 × local_max_similarity
   ```

### Data Flow

```
Upload: Image → Global Embedding → PostgreSQL + Qdrant
Search: Query → Text Embedding → Qdrant Search → Local Re-rank → Results
```

## 🚀 Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Qdrant (Docker recommended)
- CUDA-capable GPU (RTX 3050 or better)

### 1. Start Qdrant

```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 2. Setup PostgreSQL

```bash
# Create database
createdb media_search

# Or use existing PostgreSQL instance
# Update credentials in backend/config.py
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Start server
python main.py
```

The backend will:
- Initialize PostgreSQL schema
- Create Qdrant collection
- Download SigLIP model (~1GB)
- Start API on http://localhost:8000

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend will be available at http://localhost:3000

## 📖 API Documentation

### Upload Image

```bash
POST /upload
Content-Type: multipart/form-data

Response:
{
  "image_id": "uuid",
  "file_path": "storage/images/uuid.jpg",
  "message": "Image uploaded and indexed successfully"
}
```

### Search Images

```bash
POST /search
Content-Type: application/json

{
  "query": "man walking at night",
  "top_k": 10
}

Response:
{
  "query": "man walking at night",
  "results": [
    {
      "image_id": "uuid",
      "image_url": "/images/uuid.jpg",
      "score": 0.85,
      "global_score": 0.82,
      "local_score": 0.91
    }
  ],
  "total": 10
}
```

## 🎨 Tech Stack

**Backend**
- FastAPI - Modern Python web framework
- SigLIP - Vision-language embeddings
- Qdrant - Vector similarity search
- PostgreSQL - Metadata storage
- PyTorch - Deep learning framework

**Frontend**
- React 18 - UI framework
- Vite - Build tool
- Axios - HTTP client
- Modern CSS - Glassmorphism & animations

## 📁 Project Structure

```
Media-Search/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── database.py          # DB initialization
│   ├── embedding_service.py # SigLIP service
│   ├── models.py            # Pydantic models
│   └── requirements.txt     # Python deps
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main component
│   │   ├── App.css          # Styles
│   │   └── main.jsx         # Entry point
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── storage/
    └── images/              # Local image storage
```

## 🔧 Configuration

Edit `backend/config.py` to customize:

- Database connections
- Model selection
- Search parameters (Top-K, score weights)
- Storage paths

## 🎯 Performance

Optimized for RTX 3050:
- Global embeddings computed once at upload
- Local embeddings only for Top-50 candidates
- 5 crops per image (manageable GPU load)
- Typical search time: 2-5 seconds

## 🚀 Future Enhancements

- [ ] Cloud storage integration (S3, GCS)
- [ ] Metadata extraction and filtering
- [ ] VLM integration for advanced queries
- [ ] Batch upload processing
- [ ] Search history and favorites
- [ ] Multi-modal search (image + text)

## 📝 License

MIT
