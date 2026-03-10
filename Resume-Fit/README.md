# 🎯 Resume-Fit

**AI-Powered Multi-Agent Resume Tailoring System**

A production-grade application that uses Claude (writer) and GPT-4 (scorer) agents to generate ATS-optimized, role-specific resumes from job descriptions.

![Architecture](https://img.shields.io/badge/Architecture-Multi--Agent-blue)
![Backend](https://img.shields.io/badge/Backend-FastAPI-green)
![Frontend](https://img.shields.io/badge/Frontend-React-61DAFB)
![Cloud](https://img.shields.io/badge/Cloud-AWS-orange)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend                            │
│  • Job Description Input    • Live Resume Preview           │
│  • Settings Management      • Download DOCX/PDF             │
└─────────────────────────────────┬───────────────────────────┘
                                  │ REST API
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Claude    │  │   GPT-4     │  │   DOCX Generator    │ │
│  │   Writer    │  │   Scorer    │  │   (python-docx)     │ │
│  │   Agent     │  │   Agent     │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│         │                │                    │             │
│         └────────────────┼────────────────────┘             │
│                          ▼                                   │
│              ┌─────────────────────┐                        │
│              │    Orchestrator     │                        │
│              │  (Feedback Loop)    │                        │
│              └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### Level 1 (Current)
- ✅ Paste JD → Generate tailored resume
- ✅ Claude writes, GPT-4 scores with strict ATS criteria
- ✅ Iterative refinement loop (max 3 iterations, target 85+ score)
- ✅ Live preview with exact resume formatting
- ✅ Download as DOCX or PDF
- ✅ Fulltime vs Contract mode (different formats)

### Level 1.5 (Multi-User) - Planned
- 🔲 User authentication (Google OAuth)
- 🔲 Per-user customizable guidelines
- 🔲 Upload personal resume template
- 🔲 Resume generation history

### Level 2 (Automation) - Planned
- 🔲 Job API integration (auto-fetch matching jobs)
- 🔲 Background resume generation
- 🔲 Email notifications
- 🔲 Application tracking dashboard

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Tailwind CSS, React Router |
| Backend | FastAPI, Python 3.11, Pydantic |
| AI Models | Claude Sonnet 4 (Writer), GPT-4o (Scorer) |
| Document Gen | python-docx, LibreOffice (PDF) |
| Database | PostgreSQL (Level 1.5+) |
| Cloud | AWS EC2, S3, RDS |
| Auth | Google OAuth 2.0 (Level 1.5+) |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Anthropic API Key
- OpenAI API Key

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your API keys

# Run backend
uvicorn main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## 📁 Project Structure

```
Resume-Fit/
├── backend/
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Settings & env vars
│   ├── agents/
│   │   ├── writer_agent.py     # Claude integration
│   │   ├── scorer_agent.py     # GPT-4 strict scoring
│   │   ├── orchestrator.py     # Feedback loop
│   │   └── docx_generator.py   # Resume document generation
│   ├── routers/
│   │   ├── generate.py         # /api/generate endpoints
│   │   ├── preview.py          # /api/preview endpoints
│   │   └── health.py           # Health check
│   ├── defaults/
│   │   └── guidelines.md       # 25-rule resume writing guide
│   └── output/                 # Generated files
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Home.jsx        # Landing page
│   │   │   └── Generate.jsx    # Main generation page
│   │   ├── components/
│   │   │   ├── ResumePreview.jsx   # Live preview
│   │   │   ├── JobInput.jsx        # JD input
│   │   │   └── ScoreCard.jsx       # Score display
│   │   └── services/
│   │       └── api.js          # API client
│   └── package.json
│
└── deployment/
    ├── ec2-setup.sh            # AWS EC2 setup script
    └── nginx.conf              # Nginx configuration
```

---

## 🎯 How It Works

### Multi-Agent System

1. **Writer Agent (Claude)**
   - Analyzes JD for ownership areas
   - Generates tailored resume content
   - Follows 25-rule guidelines for realism

2. **Scorer Agent (GPT-4)**
   - Strict ATS scoring (not just keyword matching)
   - Requires evidence in work experience bullets
   - Penalizes generic/forced wording
   - Returns detailed feedback

3. **Orchestrator**
   - Runs writer → scorer loop
   - Passes feedback to writer for refinement
   - Continues until score ≥ 85 or max 3 iterations

### Scoring Criteria

| Category | Weight | Description |
|----------|--------|-------------|
| Must-Have Evidence | 25% | Core skills backed by work bullets |
| Experience Alignment | 20% | Role fit with JD requirements |
| Wording Realism | 15% | Natural vs AI-generated language |
| Skills Credibility | 15% | Believable tool usage |
| Domain Coherence | 10% | Consistent expertise areas |
| Impact Specificity | 10% | Concrete metrics & outcomes |
| Format Clarity | 5% | Clean, ATS-friendly format |

---

## 📊 Interview Talking Points

This project demonstrates:

- **Multi-Agent AI Systems** - Orchestrating Claude + GPT-4 with feedback loops
- **Prompt Engineering** - Detailed guidelines for realistic output
- **Full-Stack Development** - React frontend + FastAPI backend
- **Document Generation** - Programmatic DOCX/PDF creation
- **Cloud Deployment** - AWS EC2 with production configuration
- **API Design** - RESTful endpoints with proper error handling

---

## 📝 License

MIT License - Feel free to use and modify!

---

## 👤 Author

**Srikanth Manchimchetty**
- LinkedIn: [srikanthmanchimchetty](https://www.linkedin.com/in/srikanthmanchimchetty)
- GitHub: [Srikanthsanju](https://github.com/Srikanthsanju)
