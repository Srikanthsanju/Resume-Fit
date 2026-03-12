"""
Writer Agent

Designed to pair with scorer_agent_final.py.
Key features:
- accepts scorer feedback with concrete rewrites
- writes Fulltime more selectively and Contract more broadly
- follows guidelines while letting scorer feedback override generic template habits
- produces more grounded object + action + system + result bullets
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

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
These are not tool names. They are the real decisions and responsibilities the role owns.

Examples:
- inference platform design
- model deployment and monitoring
- retrieval architecture
- CI/CD for ML services
- AI standards and review guidance
- vendor evaluation and technical due diligence

JOB DESCRIPTION:
{job_description}

Return only a JSON array.
"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        try:
            match = re.search(r"\[.*\]", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(text)
        except Exception:
            return [line.strip("- ").strip() for line in text.splitlines() if line.strip()][:7]

    def generate_resume(
        self,
        job_description: str,
        feedback: Optional[str] = None,
        role_type: str = "AI Engineer",
        job_type: str = "Fulltime",
        scorer_feedback: Optional[Dict[str, Any]] = None,
    ) -> dict:
        ownership_areas = self.identify_ownership_areas(job_description)
        scorer_feedback = scorer_feedback or {}
        writer_feedback = scorer_feedback.get("writer_feedback", {})

        date_rules = {
            "Fulltime": {
                "experience_years": "5+ years",
                "cognizant_dates": "Jun 2020 - Oct 2021",
                "amrita_dates": "Jun 2016 - May 2020",
            },
            "Contract": {
                "experience_years": "7+ years",
                "cognizant_dates": "Jun 2018 - Oct 2021",
                "amrita_dates": "Jun 2014 - May 2018",
            },
        }
        active_dates = date_rules["Contract" if job_type.lower() == "contract" else "Fulltime"]

        example_block = """
GOOD BULLETS
1. Built SageMaker training and deployment workflows for batch and real-time inference, then tracked model versions to support controlled releases.
2. Processed call transcripts and policy documents to generate features used by classification and retrieval models across support workflows.
3. Implemented monitoring for prediction drift and response quality, then triggered retraining jobs when service thresholds were breached.
4. Developed a RAG workflow that retrieved grounded content from a vector index and injected context into GPT responses for support teams.
5. Provided solution-level AI design guidance for model lifecycle decisions, API integration patterns, and deployment review checkpoints.

BAD BULLETS
1. Worked on SageMaker, Docker, Kubernetes, and MLflow for model deployment.
2. Responsible for AI solutions using Python and AWS.
3. Strong experience with machine learning and large language models.
4. Built end-to-end robust scalable solutions for business value.
5. Designed enterprise AI strategy and standards across the organization.

HOW TO FIX THEM
- name the object or dataset
- name the action
- name the system or service
- name the result or operational effect
- only claim architect-level ownership when the bullet actually shows reviews, standards, tradeoffs, or guidance
"""

        rewrite_examples = writer_feedback.get("rewrite_examples", [])
        rewrite_text = []
        if rewrite_examples:
            rewrite_text.append("SCORER REWRITE EXAMPLES")
            for i, item in enumerate(rewrite_examples, 1):
                rewrite_text.append(f"{i}. BAD: {item.get('bad', '')}")
                rewrite_text.append(f"   BETTER: {item.get('better', '')}")
        rewrite_block = "\n".join(rewrite_text)

        system_prompt = f"""
You are an expert resume writer specializing in tech resumes.
Your job is to generate high-ATS but believable resume content.

CANDIDATE BACKGROUND
{self.resume_details}

RULEBOOK
{self.guidelines}

TARGET CONTEXT
- Role type: {role_type}
- Job type: {job_type}
- Ownership areas from JD: {json.dumps(ownership_areas)}
- Experience positioning: {active_dates['experience_years']}
- Cognizant dates: {active_dates['cognizant_dates']}
- Amrita University dates: {active_dates['amrita_dates']}

WRITING MODE
- Fulltime mode must be more selective, grounded, and recruiter-trust oriented.
- Contract mode may be broader, more implementation-heavy, and more direct about checklist fit.
- In Fulltime mode, do not force every replaceable skill into work bullets.
- In Contract mode, broader keyword coverage is allowed if still believable.
- Some granular or replaceable tools may stay mostly in Skills.

SCORER GUIDANCE
- Top fixes: {json.dumps(scorer_feedback.get('top_fixes', []))}
- Wording gaps: {json.dumps(scorer_feedback.get('wording_gaps', []))}
- Skill gaps: {json.dumps(scorer_feedback.get('skill_gaps', []))}
- Core ownership areas to emphasize: {json.dumps(writer_feedback.get('core_ownership_areas', []))}
- Skills to emphasize in bullets: {json.dumps(writer_feedback.get('skills_to_emphasize', []))}
- Skills okay mainly in Skills section: {json.dumps(writer_feedback.get('skills_ok_in_skills_only', []))}
- Patterns to avoid: {json.dumps(writer_feedback.get('bad_patterns_to_avoid', []))}
- Summary guidance: {writer_feedback.get('summary_guidance', '')}

{example_block}

{rewrite_block}

HARD RULES
1. Follow the guideline date rules exactly for the chosen job type.
2. Summary should be about 60% target role alignment and 40% systems or production context.
3. Do not include metrics in Summary.
4. Avoid generic phrases like proven track record, demonstrated ability, strong experience, and deep expertise.
5. Use object + action + system + result style in many bullets, but vary structure naturally.
6. Do not force defense, clearance, or national-security wording unless it is clearly grounded.
7. For architect JDs, use solution design and review language before enterprise strategy language unless the profile clearly supports stronger claims.
8. Respect scorer guidance even when it is more specific than the generic rules.
9. AI content belongs mainly in Bee Data and Allied Health. BYJU'S should lean ML or analytics. Cognizant should lean software and data systems.
10. Keep the skills section aligned to JD priority.
11. Technologies are often OR conditions. Do not force every optional or replaceable skill into bullets.
12. LoRA or QLoRA can support model optimization language when relevant.
13. Computer vision or recommender system language should only be used if it sounds credible and fits the actual work.

OUTPUT FORMAT
Return only valid JSON with these keys:
{{
  "summary": ["..."],
  "skills": {{"Programming": "..."}},
  "bee_data": ["..."],
  "allied_health": ["..."],
  "byjus": ["..."],
  "cognizant": ["..."]
}}
"""

        user_prompt = f"""JOB DESCRIPTION
{job_description}
"""
        if feedback:
            user_prompt += f"""
ADDITIONAL FEEDBACK TO APPLY
{feedback}
"""
        user_prompt += "\nGenerate the resume content now. Return only valid JSON."

        response = self.client.messages.create(
            model=self.model,
            max_tokens=9000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = response.content[0].text.strip()
        try:
            if text.startswith("```"):
                text = re.sub(r'^```json?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)
            return json.loads(text)
        except json.JSONDecodeError as e:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError(f"Failed to parse Claude response as JSON: {e}")
