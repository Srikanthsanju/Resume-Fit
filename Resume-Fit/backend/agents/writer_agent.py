"""
Writer Agent - Uses Claude to generate tailored resume content

Key upgrades in this version:
1. Accepts structured scorer feedback and concrete rewrite examples.
2. Gives Claude many examples of natural vs generic bullets.
3. Makes Fulltime generation more selective and human-sounding.
4. Makes Contract generation broader and more checklist-friendly.
5. Uses scorer feedback to improve after each iteration instead of repeating the same mistakes.
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

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

Examples:
- inference platform design
- retrieval architecture
- CI/CD for ML services
- model deployment and monitoring
- API service ownership
- data quality enforcement
- evaluation strategy

JOB DESCRIPTION:
{job_description}

Return ONLY a JSON array.
"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        try:
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(text)
        except Exception:
            areas = [line.strip("- ").strip() for line in text.split("\n") if line.strip()]
            return areas[:7]

    def generate_resume(
        self,
        job_description: str,
        feedback: Optional[str] = None,
        role_type: str = "AI Engineer",
        job_type: str = "Fulltime",
        scorer_feedback: Optional[Dict[str, Any]] = None
    ) -> dict:
        ownership_areas = self.identify_ownership_areas(job_description)

        date_rules = {
            "Fulltime": {
                "experience_years": "5+ years",
                "cognizant_dates": "Jun 2020 - Oct 2021",
                "amrita_dates": "Jun 2016 - May 2020"
            },
            "Contract": {
                "experience_years": "7+ years",
                "cognizant_dates": "Jun 2018 - Oct 2021",
                "amrita_dates": "Jun 2014 - May 2018"
            }
        }
        active_dates = date_rules["Contract" if job_type.lower() == "contract" else "Fulltime"]

        scorer_feedback = scorer_feedback or {}
        writer_fb = scorer_feedback.get("writer_feedback", {})
        rewrite_examples = writer_fb.get("rewrite_examples", [])
        top_fixes = scorer_feedback.get("top_fixes", [])
        wording_gaps = scorer_feedback.get("wording_gaps", [])
        skill_gaps = scorer_feedback.get("skill_gaps", [])

        example_block = """
GOOD BULLET EXAMPLES
1. Built SageMaker training and deployment workflows for batch and real-time inference, then tracked model versions to support controlled releases.
2. Processed call transcripts and policy documents to generate features used by classification and retrieval models across support workflows.
3. Implemented monitoring for prediction drift and response quality, then triggered retraining jobs when model accuracy dropped below service thresholds.
4. Developed a RAG service that retrieved document context from a vector index and injected grounded content into LLM responses.
5. Packaged inference services in Docker and deployed them behind managed endpoints to support low-latency API requests.

BAD BULLET EXAMPLES
1. Worked on SageMaker, Docker, Kubernetes, and MLflow for model deployment.
2. Responsible for AI solutions using Python and AWS.
3. Strong experience with machine learning and large language models.
4. Built end-to-end scalable robust solutions for business value.
5. Used LangChain and OpenAI for RAG.

HOW TO IMPROVE BAD BULLETS
- Name the object or data: transcripts, policy documents, training dataset, model endpoint, vector index
- Name the action: built, deployed, monitored, tuned, triggered, packaged, processed
- Name the system: SageMaker, batch jobs, APIs, retrieval flow, model registry
- Name the outcome: reduced latency, enabled batch scoring, improved retrieval quality, supported production traffic
"""

        rewrite_block = ""
        if rewrite_examples:
            rewrite_lines = ["SCORER REWRITE EXAMPLES"]
            for i, item in enumerate(rewrite_examples, 1):
                bad = item.get("bad", "")
                better = item.get("better", "")
                rewrite_lines.append(f"{i}. BAD: {bad}")
                rewrite_lines.append(f"   BETTER: {better}")
            rewrite_block = "\n".join(rewrite_lines)

        system_prompt = f"""You are an expert resume writer specializing in tech resumes for AI and ML roles.

YOUR TASK
Generate tailored resume content for a job application. Follow the guidelines exactly and use scorer feedback to improve weak areas.

CANDIDATE BACKGROUND
{self.resume_details}

GUIDELINES
{self.guidelines}

JOB CONTEXT
- Target Role Type: {role_type}
- Job Type: {job_type}
- Ownership Areas from JD: {json.dumps(ownership_areas)}
- Use this experience positioning: {active_dates["experience_years"]}
- Use these exact date rules elsewhere in the system:
  - Cognizant: {active_dates["cognizant_dates"]}
  - Amrita University: {active_dates["amrita_dates"]}

JOB-TYPE LOGIC
- Fulltime resumes must sound more selective, tighter, and more natural.
- Contract resumes may be broader, more explicit, and slightly more checklist-aligned.
- For Fulltime resumes, do NOT force every replaceable skill into experience bullets.
- For Contract resumes, broader JD item coverage is acceptable if still believable.
- It is acceptable for some replaceable or adjacent skills to appear only in the Skills section.
- Prefer the strongest natural substitute when JD items are interchangeable.
- Example: if Python is much stronger than Java, do not force Java heavily into bullets for Fulltime.
- Example: if LangChain is the strongest supported agent framework, do not force CrewAI everywhere unless the JD requires stronger emphasis.

SUMMARY RULES
- Summary should be about 60% target-role alignment and 40% core systems, production actions, or business-operational context.
- Do not turn the summary into a pasted job title.
- Do not force defense, national security, or clearance wording into the summary unless extensively proven.
- Do not include metrics in summary.

{example_block}

{rewrite_block}

SCORER GUIDANCE TO APPLY
- Top fixes: {json.dumps(top_fixes)}
- Wording gaps: {json.dumps(wording_gaps)}
- Skill gaps: {json.dumps(skill_gaps)}
- Core ownership areas to emphasize: {json.dumps(writer_fb.get("core_ownership_areas", []))}
- Skills to emphasize in bullets: {json.dumps(writer_fb.get("skills_to_emphasize", []))}
- Skills that can stay mostly in Skills section: {json.dumps(writer_fb.get("skills_ok_in_skills_only", []))}
- Patterns to avoid: {json.dumps(writer_fb.get("bad_patterns_to_avoid", []))}
- Summary guidance: {writer_fb.get("summary_guidance", "")}

CRITICAL RULES
1. Follow the length distribution for each section based on job type.
2. Use verbatim phrases from the JD only when natural.
3. At least 60% of bullets must show ownership, decisions, or system-shaping work.
4. No phrase root should repeat more than once per section unless clearly necessary.
5. Skills section order must mirror JD priority.
6. AI content only in Bee Data and Allied Health.
7. ML content in BYJU'S and software-focused content in Cognizant.
8. Around 70% of bullets should have measurable signals and around 60% should include specific numbers when natural.
9. Technologies are often OR conditions. Do not force every replaceable JD tool into bullets.
10. The resume must sound like a real engineer, not an AI keyword generator.
11. Do not force defense or clearance branding.
12. LoRA or QLoRA level model optimization is enough to support LLM training and optimization language when relevant.
13. Computer vision or recommender system language should only be used if placed naturally and credibly.
14. Avoid bad bullets that only say used, worked on, responsible for, or strong experience with.
15. Every important bullet should ideally show this pattern in a natural way: object or data + action + system + result.

OUTPUT FORMAT
Return a JSON object with these exact keys:
{{
    "summary": ["bullet 1", "bullet 2", "..."],
    "skills": {{
        "Programming": "Python 3.11+, ..."
    }},
    "bee_data": ["bullet 1", "bullet 2", "..."],
    "allied_health": ["bullet 1", "bullet 2", "..."],
    "byjus": ["bullet 1", "bullet 2", "..."],
    "cognizant": ["bullet 1", "bullet 2", "..."]
}}
"""

        user_prompt = f"""JOB DESCRIPTION
{job_description}

"""
        if feedback:
            user_prompt += f"""ADDITIONAL FEEDBACK TO INCORPORATE
{feedback}

"""

        user_prompt += """Generate the tailored resume content. Return ONLY valid JSON with no markdown."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=9000,
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt
        )

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

    scorer_feedback = {
        "top_fixes": ["Add more grounded outcomes and reduce generic summary claims."],
        "writer_feedback": {
            "core_ownership_areas": ["model deployment and inference workflows", "llm application and orchestration workflows"],
            "skills_to_emphasize": ["python", "aws", "langchain", "llm"],
            "skills_ok_in_skills_only": ["crewai"],
            "bad_patterns_to_avoid": ["Do not stack 4+ tools in one bullet."],
            "rewrite_examples": [
                {
                    "bad": "Worked on AWS and LangChain for AI solutions.",
                    "better": "Built LangChain-based retrieval workflows on AWS to support grounded document responses in production."
                }
            ],
            "summary_guidance": "Keep summary closer to systems and production actions."
        }
    }

    result = writer.generate_resume(test_jd, role_type="AI Engineer", job_type="Fulltime", scorer_feedback=scorer_feedback)
    print(json.dumps(result, indent=2)[:800] + "...")
