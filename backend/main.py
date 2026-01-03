from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import init_db
from config import IMAGES_DIR, THUMBNAILS_DIR
from routers import auth, images, search, shares, faces
from routers.sse import router as sse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    print("🚀 Starting up...")
    await init_db()
    print("✅ Database initialized")
    
    # Lazy load ML models on first use (saves startup time)
    yield
    
    # Shutdown
    print("👋 Shutting down...")


app = FastAPI(
    title="Media Search API",
    description="Intelligent image search with SigLIP embeddings and VLM-powered deep search",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static file directories
app.mount("/static/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")
app.mount("/static/thumbnails", StaticFiles(directory=str(THUMBNAILS_DIR)), name="thumbnails")

# Include routers
app.include_router(auth, prefix="/auth", tags=["Authentication"])
app.include_router(images, prefix="/images", tags=["Images"])
app.include_router(search, prefix="/search", tags=["Search"])
app.include_router(shares, prefix="/shares", tags=["Sharing"])
app.include_router(faces, prefix="/faces", tags=["Face Recognition"])
app.include_router(sse, prefix="/events", tags=["Events"])


@app.get("/")
async def root():
    return {
        "message": "Media Search API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
