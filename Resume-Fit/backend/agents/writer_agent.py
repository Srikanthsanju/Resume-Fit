"""
Writer Agent - Uses Claude to generate tailored resume content
"""

import os
import json
import re
from pathlib import Path
from typing import List

import anthropic


class WriterAgent:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

        config_dir = Path(__file__).parent.parent / "config"
        defaults_dir = Path(__file__).parent.parent / "defaults"

        self.resume_details = ""
        details_path = config_dir / "resume_details.md"
        if details_path.exists():
            self.resume_details = details_path.read_text(encoding="utf-8")

        self.guidelines = ""
        guidelines_path = defaults_dir / "guidelines.md"
        if guidelines_path.exists():
            self.guidelines = guidelines_path.read_text(encoding="utf-8")

    def identify_ownership_areas(self, job_description: str) -> List[str]:
        prompt = f"""Analyze this job description and extract 5-7 Core Technical Ownership Areas.

These are NOT tools. These are the real decisions and responsibilities the role owns end-to-end.

Examples of ownership areas:
- inference platform design
- retrieval architecture
- CI/CD for ML services
- model deployment and monitoring
- API service ownership
- data quality enforcement
- evaluation strategy

JOB DESCRIPTION:
{job_description}

Return ONLY a JSON array of ownership areas. Example:
["inference platform design", "RAG system architecture", "model evaluation framework"]
"""
        response = self.client.messages.create(model=self.model, max_tokens=500, messages=[{"role": "user", "content": prompt}])
        text = response.content[0].text.strip()
        try:
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(text)
        except Exception:
            areas = [line.strip("- ").strip() for line in text.split("\n") if line.strip()]
            return areas[:7]

    def generate_resume(self, job_description: str, feedback: str = None, role_type: str = "AI Engineer", job_type: str = "Fulltime") -> dict:
        ownership_areas = self.identify_ownership_areas(job_description)
        date_rules = {
            "Fulltime": {"experience_years": "5+ years", "cognizant_dates": "Jun 2020 - Oct 2021", "amrita_dates": "Jun 2016 - May 2020"},
            "Contract": {"experience_years": "7+ years", "cognizant_dates": "Jun 2018 - Oct 2021", "amrita_dates": "Jun 2014 - May 2018"},
        }
        active_dates = date_rules["Contract" if job_type.lower() == "contract" else "Fulltime"]

        system_prompt = f"""You are an expert resume writer specializing in tech resumes for AI and ML roles.

## YOUR TASK
Generate tailored resume content for a job application. You must follow ALL the guidelines exactly.

## CANDIDATE'S BACKGROUND
{self.resume_details}

## RESUME WRITING GUIDELINES
{self.guidelines}

## ADDITIONAL CONTEXT
- Target Role Type: {role_type}
- Job Type: {job_type}
- Ownership Areas from JD: {json.dumps(ownership_areas)}
- Use this experience positioning: {active_dates['experience_years']}
- Use these exact date rules when producing role or education metadata elsewhere in the system:
  - Cognizant: {active_dates['cognizant_dates']}
  - Amrita University: {active_dates['amrita_dates']}

## JOB-TYPE LOGIC
- Fulltime resumes must sound more selective, tighter, and more natural.
- Contract resumes may be broader, more explicit, and slightly more checklist-aligned.
- For Fulltime resumes, do NOT force every replaceable skill into experience bullets.
- For Contract resumes, broader JD item coverage is acceptable if still believable.
- It is acceptable for some replaceable or adjacent skills to appear only in the Skills section.
- Prefer the strongest natural substitute when JD items are interchangeable.
- Example: if Python is much stronger than Java, do not force Java heavily into bullets for Fulltime.
- Example: if LangChain is the strongest supported agent framework, do not force CrewAI everywhere unless the JD requires stronger emphasis.

## SUMMARY RULES
- Summary should be about 60% target-role alignment and 40% core systems, production actions, or business-operational context.
- Do not turn the summary into a pasted job title.
- Do not force defense, national security, or clearance wording into the summary unless extensively proven.
- Do not include metrics in summary.

## OUTPUT FORMAT
Return a JSON object with these exact keys:
{{
    "summary": ["bullet 1", "bullet 2", ...],
    "skills": {
        "Programming": "Python 3.11+, ..."
    },
    "bee_data": ["bullet 1", "bullet 2", ...],
    "allied_health": ["bullet 1", "bullet 2", ...],
    "byjus": ["bullet 1", "bullet 2", ...],
    "cognizant": ["bullet 1", "bullet 2", ...]
}}

## CRITICAL RULES
1. Follow the length distribution for each section based on job type
2. Use verbatim phrases from the JD only when natural
3. At least 60% of bullets must show ownership, decisions, or system-shaping work
4. No phrase root should repeat more than once per section unless clearly necessary
5. Skills section order must mirror JD priority
6. AI content only in Bee Data and Allied Health
7. ML content in BYJU'S and software-focused content in Cognizant
8. Around 70% of bullets should have measurable signals and around 60% should include specific numbers when natural
9. Technologies are often OR conditions. Do not force every replaceable JD tool into bullets
10. The resume must sound like a real engineer, not an AI keyword generator
11. Do not force defense or clearance branding
12. LoRA or QLoRA level model optimization is enough to support LLM training and optimization language when it is relevant
13. Computer vision or recommender system language should only be used if placed naturally and credibly
"""

        user_prompt = f"""## JOB DESCRIPTION
{job_description}

"""
        if feedback:
            user_prompt += f"""## FEEDBACK TO INCORPORATE
Address these points carefully:
{feedback}

"""
        user_prompt += """Generate the tailored resume content. Return ONLY valid JSON, no markdown."""
        response = self.client.messages.create(model=self.model, max_tokens=8000, messages=[{"role": "user", "content": user_prompt}], system=system_prompt)
        text = response.content[0].text.strip()
        try:
            if text.startswith("```"):
                text = re.sub(r'^```json?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)
            return json.loads(text)
        except json.JSONDecodeError as e:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError(f"Failed to parse Claude response as JSON: {e}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    writer = WriterAgent()
    test_jd = """
Senior AI Engineer
Requirements:
- Python
- LangChain or CrewAI
- AWS deployment
"""
    result = writer.generate_resume(test_jd, role_type="AI Engineer", job_type="Fulltime")
    print(json.dumps(result, indent=2)[:500] + "...")
