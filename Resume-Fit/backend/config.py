"""
Configuration settings for Resume-Fit backend
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # API Keys
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Model settings
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    # Generation settings
    MIN_SCORE: int = 85
    MAX_ITERATIONS: int = 3
    
    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent
    OUTPUT_DIR: Path = BASE_DIR / "output"
    DEFAULTS_DIR: Path = BASE_DIR / "defaults"
    CONFIG_DIR: Path = BASE_DIR / "config"
    
    class Config:
        env_file = ".env"


settings = Settings()

# Ensure directories exist
settings.OUTPUT_DIR.mkdir(exist_ok=True)
