# Media Search - Intelligent Image Search System

An intelligent image search system with SigLIP embeddings, VLM-powered deep search, face recognition, and multi-user support.

## Features

- **Fast Normal Search**: SigLIP embedding-based similarity search
- **Accurate Deep Search**: Metadata matching + VLM validation
- **Face Recognition**: Automatic face detection, clustering, and naming
- **Multi-User**: Secure authentication with user isolation
- **Sharing**: Share photos with other users

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy
- **Frontend**: React, Vite
- **Database**: PostgreSQL (users), Qdrant (vectors)
- **ML**: SigLIP (embeddings), SmolVLM (metadata)
- **Face Recognition**: face_recognition library

## Quick Start

### 1. Start Docker Services

```bash
docker-compose up -d
```

This starts PostgreSQL and Qdrant.

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

### 4. Access the App

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Environment Variables

Copy `.env.example` to `.env` and configure:

- `DATABASE_URL`: PostgreSQL connection string
- `QDRANT_HOST`: Qdrant server host
- `JWT_SECRET`: Secret key for JWT tokens (change in production!)
- `DEVICE`: `cuda` for GPU, `cpu` for CPU-only

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login
- `GET /auth/me` - Get current user

### Images
- `POST /images/upload` - Upload images
- `GET /images/` - List images
- `GET /images/{id}` - Get image
- `DELETE /images/{id}` - Delete image

### Search
- `GET /search/normal?q=query` - Fast embedding search
- `GET /search/deep?q=query` - Accurate deep search

### Faces
- `GET /faces/clusters` - List face clusters
- `PUT /faces/clusters/{id}/name` - Name a person
- `GET /faces/search?name=John` - Search by person

### Sharing
- `POST /shares/` - Share image with user
- `GET /shares/with-me` - Images shared with me

## Search Modes

### Normal Search (Fast)
- Uses SigLIP text→image embedding similarity
- Very fast, good for general browsing
- Best for simple queries

### Deep Search (Accurate)
- Expands candidate pool with embeddings
- Applies soft metadata matching
- Uses controlled relaxation for near-matches
- Optional VLM validation for top results
- Best for complex, specific queries

## License

MIT
