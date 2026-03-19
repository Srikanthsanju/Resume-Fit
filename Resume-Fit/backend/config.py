import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Config:
    # Model Selection
    WRITER_MODEL = os.getenv("WRITER_MODEL", "claude-3-5-sonnet-20241022")
    SCORER_MODEL = os.getenv("SCORER_MODEL", "gpt-4o")
    
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