from app.routers.auth import router as auth_router
from app.routers.keywords import router as keywords_router
from app.routers.jobs import router as jobs_router
from app.routers.settings import router as settings_router
from app.routers.videos import router as videos_router

__all__ = [
    "auth_router",
    "keywords_router", 
    "jobs_router",
    "settings_router",
    "videos_router"
]
