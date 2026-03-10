"""
Resume generation endpoints
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from pathlib import Path
import json

from agents.orchestrator import ResumeOrchestrator
from agents.docx_generator import ResumeGenerator
from config import settings

router = APIRouter()


class GenerateRequest(BaseModel):
    job_description: str
    role_type: str = "AI Engineer"  # "AI Engineer", "Data Scientist", "Software Engineer"
    job_type: str = "Fulltime"  # "Fulltime" or "Contract"
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    
    # Optional: Custom guidelines (for Level 1.5 multi-user)
    writer_guidelines: Optional[str] = None
    scorer_guidelines: Optional[str] = None


class GenerateResponse(BaseModel):
    success: bool
    iterations: int
    final_score: int
    passed: bool
    resume_content: Dict[str, Any]
    score_details: Dict[str, Any]
    docx_url: Optional[str] = None
    pdf_url: Optional[str] = None
    history: List[Dict[str, Any]] = []


class QuickPreviewRequest(BaseModel):
    job_description: str
    role_type: str = "AI Engineer"
    job_type: str = "Fulltime"


@router.post("/generate", response_model=GenerateResponse)
async def generate_resume(request: GenerateRequest):
    """
    Generate a tailored resume from job description.
    
    The orchestrator runs Claude (writer) and GPT-4 (scorer) in a loop
    until the score reaches 85+ or max 3 iterations.
    """
    
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")
    
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    try:
        # Initialize orchestrator
        orchestrator = ResumeOrchestrator(
            anthropic_key=settings.ANTHROPIC_API_KEY,
            openai_key=settings.OPENAI_API_KEY
        )
        
        # Run generation
        result = orchestrator.process_job(
            job_description=request.job_description,
            role_type=request.role_type,
            job_type=request.job_type,
            company_name=request.company_name,
            job_title=request.job_title
        )
        
        # Generate DOCX
        generator = ResumeGenerator(output_dir=str(settings.OUTPUT_DIR))
        docx_path, pdf_path = generator.generate(
            resume_content=result["resume_content"],
            company_name=request.company_name,
            job_title=request.job_title,
            mode=request.job_type
        )
        
        # Build response
        score = result["score"]
        
        return GenerateResponse(
            success=True,
            iterations=result["iterations"],
            final_score=score.get("score", 0),
            passed=score.get("passed", False),
            resume_content=result["resume_content"],
            score_details=score,
            docx_url=f"/files/{docx_path.name}" if docx_path else None,
            pdf_url=f"/files/{pdf_path.name}" if pdf_path else None,
            history=result.get("history", [])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/quick-preview")
async def quick_preview(request: QuickPreviewRequest):
    """
    Generate a single iteration preview without full scoring loop.
    Faster for testing and preview purposes.
    """
    
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")
    
    try:
        from agents.writer_agent import WriterAgent
        
        writer = WriterAgent(api_key=settings.ANTHROPIC_API_KEY)
        
        # Single generation (no scoring loop)
        resume_content = writer.generate_resume(
            job_description=request.job_description,
            feedback=None,
            role_type=request.role_type,
            job_type=request.job_type
        )
        
        return {
            "success": True,
            "resume_content": resume_content,
            "note": "Quick preview without scoring. Use /generate for full optimization."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}")
async def download_file(filename: str):
    """Download generated resume file."""
    
    file_path = settings.OUTPUT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if filename.endswith(".pdf"):
        media_type = "application/pdf"
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type
    )
