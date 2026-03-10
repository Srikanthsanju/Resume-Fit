"""
Resume-Fit Backend - FastAPI Application
Multi-Agent Resume Generation System
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from routers import generate, preview, health
from config import settings

app = FastAPI(
    title="Resume-Fit API",
    description="AI-Powered Multi-Agent Resume Tailoring System",
    version="1.0.0",
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount output directory for file downloads
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
app.mount("/files", StaticFiles(directory=str(output_dir)), name="files")

# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(generate.router, prefix="/api", tags=["Generate"])
app.include_router(preview.router, prefix="/api", tags=["Preview"])


@app.get("/")
async def root():
    return {
        "name": "Resume-Fit API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
