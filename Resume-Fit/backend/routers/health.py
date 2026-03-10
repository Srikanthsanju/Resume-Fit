"""
Health check endpoints
"""

from fastapi import APIRouter
from config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Check API health and configuration status."""
    return {
        "status": "healthy",
        "anthropic_configured": bool(settings.ANTHROPIC_API_KEY),
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "models": {
            "writer": settings.CLAUDE_MODEL,
            "scorer": settings.OPENAI_MODEL,
        },
    }
