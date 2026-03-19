"""
Health check endpoints
"""

from fastapi import APIRouter
from ..config import settings
import os

router = APIRouter()


@router.get("/health")
async def health_check():
    """Check API health and configuration status."""
    return {
        "status": "healthy",
        "anthropic_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "models": {
            "writer": settings.WRITER_MODEL,
            "scorer": settings.SCORER_MODEL,
        },
    }