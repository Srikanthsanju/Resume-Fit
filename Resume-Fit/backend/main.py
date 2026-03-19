from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from agents.orchestrator import ResumeOrchestrator
from config import settings

app = FastAPI(title="Resume-Fit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings.OUTPUT_DIR.mkdir(exist_ok=True)
app.mount("/files", StaticFiles(directory=str(settings.OUTPUT_DIR)), name="files")

orchestrator = ResumeOrchestrator()

# FIXED: Matches the React frontend payload exactly
class ResumeRequest(BaseModel):
    job_description: str
    job_type: str 
    role_type: str
    company_name: Optional[str] = ""
    job_title: Optional[str] = ""

@app.post("/api/generate")
async def generate_resume(req: ResumeRequest):
    # HIGH VISIBILITY LOGGING
    print("\n" + "="*60)
    print("🟢 NEW API REQUEST RECEIVED: /api/generate")
    print(f"➜ Job Type:   {req.job_type}")
    print(f"➜ Role Type:  {req.role_type}")
    print(f"➜ Company:    {req.company_name}")
    print(f"➜ Title:      {req.job_title}")
    print(f"➜ JD Length:  {len(req.job_description)} characters")
    print("="*60 + "\n")

    try:
        result = orchestrator.process_job(
            jd=req.job_description,
            job_type=req.job_type,
            company_name=req.company_name,
            job_title=req.job_title
        )
        # FIXED: Returning the result directly so React can read result.docx_url
        return result 
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))