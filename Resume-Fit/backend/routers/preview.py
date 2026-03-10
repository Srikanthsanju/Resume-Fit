"""
Resume preview endpoints - Returns HTML preview matching DOCX format
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

router = APIRouter()


class PreviewRequest(BaseModel):
    resume_content: Dict[str, Any]
    mode: str = "Fulltime"  # "Fulltime" or "Contract"


# Job data (will be dynamic in Level 1.5)
JOBS_DATA = [
    {
        "key": "bee_data",
        "company": "Bee Data Technologies,",
        "location": "Atlanta, GA",
        "dates": "Oct 2025 - Current",
        "title": "AI Engineer",
        "description": "Design and implement GenAI solutions using Large Language Models building RAG architectures, developing Python APIs with FastAPI, and deploying models on AWS infrastructure.",
        "environment": "Python 3.11, FastAPI, LangChain, LangGraph, LlamaIndex, PyTorch, Hugging Face, AWS (SageMaker, EC2, EKS, RDS, S3), Kubeflow, MLflow, Apache Spark, Docker, Kubernetes, PostgreSQL, Pinecone, Git.",
    },
    {
        "key": "allied_health",
        "company": "Allied Health Agency,",
        "location": "Dallas, TX",
        "dates": "Aug 2023 - Oct 2025",
        "title": "AI/ML Engineer",
        "description": "Build ML-powered applications and data pipelines for healthcare operations. Develop Python APIs integrating AI models, implement RAG workflows for document search, and deploy services on AWS infrastructure.",
        "environment": "Python 3.11, FastAPI, LangChain, Scikit-learn, AWS (EC2, RDS, S3, Lambda), PostgreSQL, Pandas, Docker.",
    },
    {
        "key": "byjus",
        "company": "BYJU'S,",
        "location": "Bangalore, India",
        "dates": "Oct 2021 - Aug 2023",
        "title": "Data Engineer",
        "description": "Build ML models and analytics platforms for recruitment and business development. Develop predictive algorithms using Python and Scikit-learn, create data pipelines with PySpark, and implement dashboards.",
        "environment": "Python 3.8, Scikit-learn, XGBoost, PySpark, GCP (BigQuery, Dataproc, Cloud Functions), Power BI, Pandas, NumPy, Git.",
    },
    {
        "key": "cognizant",
        "company": "Cognizant Technology Solutions,",
        "location": "Bangalore, India",
        "dates": "Jun 2019 - Oct 2021",
        "title": "Program Analyst",
        "description": "Develop software solutions for Product Lifecycle Management systems and financial data automation for enterprise clients.",
        "environment": "Python 3.7, Pandas, openpyxl, JavaScript, SQL Server 2016, SSIS, T-SQL, Visual Studio, Git.",
    },
]

EDUCATION_DATA = [
    {
        "university": "University of North Texas,",
        "location": "Dallas, TX",
        "degree": "Masters of Science in Advanced Data Analytics",
        "dates": "Aug 2023 - Dec 2024",
        "coursework": "Machine Learning, Large Data Visualization, LLM, Cloud Platforms for Data Engineering, Database Systems and SQL Programming",
    },
    {
        "university": "Amrita University,",
        "location": "Bangalore, India",
        "degree": "Bachelor of Technology in Computer Science Engineering",
        "dates": "Jun 2015 - May 2019",
        "coursework": "Data Structures and Algorithms, Database Management Systems and Software Engineering",
    },
]


@router.post("/preview")
async def generate_preview(request: PreviewRequest):
    """
    Generate HTML preview of resume that matches the DOCX format.
    Used for live preview in the frontend.
    """
    
    content = request.resume_content
    mode = request.mode
    
    # Build HTML
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Times New Roman', Times, serif;
            font-size: 10pt;
            line-height: 1.2;
            padding: 0.42in 0.48in;
            max-width: 8.5in;
            margin: 0 auto;
            background: white;
        }}
        .name {{
            font-size: 16pt;
            font-weight: bold;
            text-align: center;
            margin-bottom: 2pt;
        }}
        .contact {{
            font-size: 10pt;
            text-align: center;
            margin-bottom: 7pt;
        }}
        .contact a {{
            color: #0563C1;
            text-decoration: underline;
        }}
        .section-header {{
            font-size: 11pt;
            font-weight: bold;
            margin-top: 10pt;
            margin-bottom: 4pt;
            border-bottom: 1px solid #000;
            padding-bottom: 1pt;
        }}
        .bullet {{
            margin-left: 0.26in;
            text-indent: -0.18in;
            padding-left: 0.18in;
            margin-bottom: 0;
        }}
        .bullet::before {{
            content: "• ";
        }}
        .skill-line {{
            margin-left: 0.04in;
            margin-bottom: 0;
        }}
        .skill-category {{
            font-weight: bold;
        }}
        .job-header {{
            display: flex;
            justify-content: space-between;
            margin-top: 6pt;
            margin-left: 0.04in;
        }}
        .job-company {{
            font-weight: bold;
        }}
        .job-title {{
            font-weight: bold;
            margin-left: 0.04in;
            margin-bottom: 1pt;
        }}
        .job-description {{
            margin-left: 0.04in;
            margin-bottom: 2pt;
        }}
        .responsibilities-label {{
            font-weight: bold;
            margin-left: 0.04in;
            margin-top: 1pt;
            margin-bottom: 1pt;
        }}
        .environment {{
            margin-left: 0.04in;
            margin-top: 3pt;
            margin-bottom: 2pt;
        }}
        .environment-label {{
            font-weight: bold;
        }}
        .edu-header {{
            display: flex;
            justify-content: space-between;
            margin-top: 5pt;
            margin-left: 0.04in;
        }}
        .edu-school {{
            font-weight: bold;
        }}
        .edu-degree {{
            margin-left: 0.04in;
        }}
        .edu-coursework {{
            margin-left: 0.04in;
            margin-bottom: 2pt;
        }}
        .coursework-label {{
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="name">SRIKANTH MANCHIMCHETTY</div>
    <div class="contact">
        mvss.1998@gmail.com  -  +1(940)703-0146  -  
        <a href="https://www.linkedin.com/in/srikanthmanchimchetty">LinkedIn</a>  -  
        Dallas, TX, USA  -  
        <a href="https://github.com/Srikanthsanju">Github</a>
    </div>
    
    <div class="section-header">SUMMARY</div>
    {"".join(f'<div class="bullet">{bullet}</div>' for bullet in content.get("summary", []))}
    
    <div class="section-header">TECHNICAL SKILLS</div>
    {"".join(f'<div class="skill-line"><span class="skill-category">{cat}:</span> {skills}</div>' for cat, skills in content.get("skills", {}).items())}
    
    <div class="section-header">PROFESSIONAL EXPERIENCE</div>
"""
    
    # Add jobs
    for job in JOBS_DATA:
        job_bullets = content.get(job["key"], [])
        
        html += f"""
    <div class="job-header">
        <div><span class="job-company">{job["company"]}</span> {job["location"]}</div>
        <div>{job["dates"]}</div>
    </div>
    <div class="job-title">{job["title"]}</div>
"""
        
        if mode == "Contract":
            html += f"""
    <div class="job-description">{job["description"]}</div>
    <div class="responsibilities-label">Responsibilities:</div>
"""
        
        for bullet in job_bullets:
            html += f'    <div class="bullet">{bullet}</div>\n'
        
        if mode == "Contract":
            html += f"""
    <div class="environment"><span class="environment-label">Environment:</span> {job["environment"]}</div>
"""
    
    # Add education
    html += """
    <div class="section-header">EDUCATION</div>
"""
    
    for edu in EDUCATION_DATA:
        html += f"""
    <div class="edu-header">
        <div><span class="edu-school">{edu["university"]}</span> {edu["location"]}</div>
        <div>{edu["dates"]}</div>
    </div>
    <div class="edu-degree">{edu["degree"]}</div>
    <div class="edu-coursework"><span class="coursework-label">Coursework:</span> {edu["coursework"]}</div>
"""
    
    html += """
</body>
</html>
"""
    
    return {
        "html": html,
        "mode": mode
    }


@router.get("/preview/empty")
async def empty_preview():
    """Return empty preview template."""
    return {
        "html": """
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            font-family: 'Times New Roman', Times, serif;
            padding: 20px;
            color: #999;
            text-align: center;
        }
    </style>
</head>
<body>
    <h3>Resume Preview</h3>
    <p>Paste a job description and click Generate to see your tailored resume here.</p>
</body>
</html>
""",
        "mode": "Fulltime"
    }
