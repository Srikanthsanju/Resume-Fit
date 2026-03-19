import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Valid Claude models (as of 2025)
VALID_CLAUDE_MODELS = [
    "claude-sonnet-4-20250514",      # Latest Sonnet 4
    "claude-3-5-sonnet-20241022",    # Claude 3.5 Sonnet v2
    "claude-3-5-sonnet-latest",      # Alias for latest 3.5
]

DEFAULT_WRITER_MODEL = "claude-sonnet-4-20250514"

class Config:
    # Model Selection - with validation
    _env_model = os.getenv("WRITER_MODEL", DEFAULT_WRITER_MODEL)
    WRITER_MODEL = _env_model if _env_model in VALID_CLAUDE_MODELS else DEFAULT_WRITER_MODEL
    SCORER_MODEL = os.getenv("SCORER_MODEL", "gpt-4o")
    
    # Log if we had to override an invalid model
    if _env_model not in VALID_CLAUDE_MODELS and _env_model != DEFAULT_WRITER_MODEL:
        print(f"⚠️  WARNING: Invalid WRITER_MODEL '{_env_model}' in .env, using '{DEFAULT_WRITER_MODEL}' instead")
    
    # Paths - Pointing to the 'backend' folder as the root
    BASE_DIR = Path(__file__).parent 
    OUTPUT_DIR = BASE_DIR / "output"
    TEMPLATE_DIR = BASE_DIR / "defaults"
    CONFIG_DIR = BASE_DIR / "config"
    
    # Mode Settings
    CONTRACT_TEMPLATE = TEMPLATE_DIR / "Contract_Template.docx"
    FULLTIME_TEMPLATE = TEMPLATE_DIR / "Srikanth_Fulltime_Tags.docx"

    # Scoring Constraints
    BULLET_TOLERANCE = 2 

settings = Config()