"""Router health check."""

from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": settings.api_version,
        "mode": settings.model_mode,
        "env": settings.env,
    }
