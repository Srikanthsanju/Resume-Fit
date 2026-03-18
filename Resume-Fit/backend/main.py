from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
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

class ResumeRequest(BaseModel):
    jd: str
    job_type: str 
    role_type: str
    company_name: str
    job_title: str

@app.post("/api/generate")
async def generate_resume(req: ResumeRequest):
    try:
        result = orchestrator.process_job(
            jd=req.jd,
            job_type=req.job_type,
            company_name=req.company_name,
            job_title=req.job_title
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))