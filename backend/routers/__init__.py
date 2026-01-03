from .auth import router as auth
from .images import router as images
from .search import router as search
from .shares import router as shares
from .faces import router as faces

__all__ = ["auth", "images", "search", "shares", "faces"]
