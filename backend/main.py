from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles as StarletteStaticFiles

import config
from database import init_databases
from services.embedding_service import get_embedding_service
from services.redis_cache import get_redis_cache

from routers.auth import router as auth_router
from routers.images import router as images_router
from routers.search import router as search_router
from routers.faces import router as faces_router

app = FastAPI(
    title="CLIP Media Search API",
    version="2.0.0",
    description="AI-powered image search using CLIP embeddings",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CORSStaticFiles(StarletteStaticFiles):
    """Static file server with CORS headers and optional download support."""

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        if scope.get("query_string"):
            query = scope["query_string"].decode()
            if "download=1" in query:
                import os
                filename = os.path.basename(path)
                response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# Static file mounts
app.mount("/images", CORSStaticFiles(directory=str(config.STORAGE_DIR)), name="images")

faces_dir = config.STORAGE_DIR / "faces"
faces_dir.mkdir(parents=True, exist_ok=True)
app.mount("/faces", CORSStaticFiles(directory=str(faces_dir)), name="faces")

# Routers
app.include_router(auth_router)
app.include_router(images_router)
app.include_router(search_router)
app.include_router(faces_router)


@app.on_event("startup")
async def startup_event():
    """Initialize databases and load models on startup."""
    print(">> Starting CLIP Media Search API...")
    init_databases()
    get_embedding_service()
    get_redis_cache()

    try:
        from services.face_service import get_face_service
        get_face_service()
    except Exception as e:
        print(f">> Warning: Face detection preload failed: {str(e)}")

    print(">> API ready!")


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "CLIP Media Search API is running",
        "model": f"{config.CLIP_MODEL} ({config.CLIP_PRETRAINED})",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)
