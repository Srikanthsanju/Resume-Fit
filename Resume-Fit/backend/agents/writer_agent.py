"""
writer_agent.py

Resume writer that consumes scorer feedback strongly.
Designed to raise ATS score without sounding forced or AI-generated.
Uses Anthropic for writing and can consume structured scorer feedback from OpenAI scorer.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import anthropic


class WriterAgent:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is missing.")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model or os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

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

    def generate_resume(self, job_description: str, feedback: Optional[str] = None, role_type: str = "AI Engineer", job_type: str = "Fulltime", scorer_feedback: Optional[Dict[str, Any]] = None) -> dict:
        scorer_feedback = self._normalize_scorer_feedback(scorer_feedback or {})
        ownership_areas = scorer_feedback["writer_feedback"].get("core_ownership_areas") or self._identify_ownership_areas(job_description)
        date_rules = {
            "Fulltime": {"experience_years": "5+ years", "cognizant_dates": "Jun 2020 - Oct 2021", "amrita_dates": "Jun 2016 - May 2020"},
            "Contract": {"experience_years": "7+ years", "cognizant_dates": "Jun 2018 - Oct 2021", "amrita_dates": "Jun 2014 - May 2018"}
        }
        active_dates = date_rules["Contract" if job_type.lower() == "contract" else "Fulltime"]
        writer_fb = scorer_feedback["writer_feedback"]
        examples_block = self._build_examples_block(writer_fb)
        guardrails_block = self._build_guardrails_block(writer_fb, scorer_feedback, job_type)
        system_prompt = f"""
You are an expert resume writer for AI, ML, platform, software, and architecture roles.

Your goal is to generate a resume that:
1. scores higher in ATS
2. sounds like a real engineer
3. does not over-claim unsupported experience
4. improves on prior scorer feedback rather than repeating the same mistakes

CANDIDATE BACKGROUND
{self.resume_details}

GUIDELINES
{self.guidelines}

JOB CONTEXT
- Target role type: {role_type}
- Job type: {job_type}
- Ownership areas from scorer or JD: {json.dumps(ownership_areas)}
- Experience positioning: {active_dates['experience_years']}
- Date rules:
  - Cognizant: {active_dates['cognizant_dates']}
  - Amrita University: {active_dates['amrita_dates']}

CORE WRITING RULES
- Fulltime resumes must sound tighter, more selective, and more natural.
- Contract resumes may be broader, more explicit, and slightly more checklist-aligned.
- In Fulltime mode, do not force every replaceable or optional JD skill into work bullets.
- In Contract mode, broader JD coverage is acceptable if still believable.
- It is acceptable for some replaceable or granular tools to appear only in the Skills section.
- Prefer stronger natural substitutes where the JD lists interchangeable tools.
- Summary must be about 60% role/JD alignment and 40% systems, production actions, or business context.
- Summary must not include metrics.
- Do not force defense, clearance, or national-security wording unless extensively proven.
- Prefer bullets that show object or data + action + system + result.
- Avoid generic phrasing such as strong experience, demonstrated ability, proven track record, and deep expertise.

{examples_block}

{guardrails_block}

OUTPUT FORMAT
Return ONLY valid JSON with these exact keys:
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
            user_prompt += f"""ADDITIONAL FEEDBACK TO APPLY
{feedback}

"""
        user_prompt += "Generate the tailored resume content now. Return only valid JSON and no markdown."
        response = self.client.messages.create(model=self.model, max_tokens=9000, system=system_prompt, messages=[{"role": "user", "content": user_prompt}])
        text = response.content[0].text.strip()
        return self._parse_resume_json(text)

    def _normalize_scorer_feedback(self, scorer_feedback: Dict[str, Any]) -> Dict[str, Any]:
        defaults = {
            "score": 0,
            "top_fixes": [],
            "wording_gaps": [],
            "skill_gaps": [],
            "writer_feedback": {
                "core_ownership_areas": [],
                "skills_to_emphasize": [],
                "skills_ok_in_skills_only": [],
                "bad_patterns_to_avoid": [],
                "rewrite_examples": [],
                "summary_guidance": "",
            }
        }
        merged = dict(defaults)
        if isinstance(scorer_feedback, dict):
            merged.update({k: v for k, v in scorer_feedback.items() if v is not None})
        if not isinstance(merged.get("top_fixes"), list):
            merged["top_fixes"] = []
        if not isinstance(merged.get("wording_gaps"), list):
            merged["wording_gaps"] = []
        if not isinstance(merged.get("skill_gaps"), list):
            merged["skill_gaps"] = []
        wf = merged.get("writer_feedback")
        if not isinstance(wf, dict):
            wf = {}
        final_wf = dict(defaults["writer_feedback"])
        final_wf.update({k: v for k, v in wf.items() if v is not None})
        for key in ["core_ownership_areas", "skills_to_emphasize", "skills_ok_in_skills_only", "bad_patterns_to_avoid", "rewrite_examples"]:
            if not isinstance(final_wf.get(key), list):
                final_wf[key] = []
        if not isinstance(final_wf.get("summary_guidance"), str):
            final_wf["summary_guidance"] = ""
        merged["writer_feedback"] = final_wf
        return merged

    def _identify_ownership_areas(self, job_description: str) -> List[str]:
        prompt = f"""Analyze this job description and extract 5 to 7 Core Technical Ownership Areas.

These are not tools. They are the real decisions and responsibilities the role owns end to end.

Examples:
- inference platform design
- retrieval architecture
- model deployment and monitoring
- CI/CD for ML services
- API integration design
- governance and review checkpoints
- feature engineering pipelines

Return ONLY a JSON array.

JOB DESCRIPTION
{job_description}
"""
        response = self.client.messages.create(model=self.model, max_tokens=500, messages=[{"role": "user", "content": prompt}])
        text = response.content[0].text.strip()
        try:
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(text)
        except Exception:
            lines = [line.strip("- ").strip() for line in text.split("\n") if line.strip()]
            return lines[:7]

    def _build_examples_block(self, writer_fb: Dict[str, Any]) -> str:
        dynamic_examples = writer_fb.get("rewrite_examples", [])
        lines = [
            "GOOD BULLET EXAMPLES",
            "1. Built SageMaker training and deployment workflows for batch and real-time inference, then tracked model versions to support controlled releases.",
            "2. Processed call transcripts and policy documents to generate features used by classification and retrieval models across support workflows.",
            "3. Implemented monitoring for prediction drift and response quality, then triggered retraining jobs when service thresholds were breached.",
            "4. Developed a RAG service that retrieved document context from a vector index and injected grounded content into LLM responses.",
            "5. Packaged inference services in Docker and deployed them behind managed endpoints to support low-latency API requests.",
            "",
            "BAD BULLET EXAMPLES",
            "1. Worked on SageMaker, Docker, Kubernetes, and MLflow for model deployment.",
            "2. Responsible for AI solutions using Python and AWS.",
            "3. Strong experience with machine learning and large language models.",
            "4. Built end-to-end scalable robust solutions for business value.",
            "5. Used LangChain and OpenAI for RAG.",
            "",
            "HOW TO IMPROVE BAD BULLETS",
            "- name the object or data: transcripts, policy documents, training dataset, model endpoint, vector index",
            "- name the action: built, deployed, monitored, tuned, triggered, packaged, processed",
            "- name the system: SageMaker, batch jobs, APIs, retrieval flow, model registry",
            "- name the outcome: reduced latency, enabled batch scoring, improved retrieval quality, supported production traffic",
        ]
        if dynamic_examples:
            lines.append("")
            lines.append("SCORER-SPECIFIC REWRITE EXAMPLES")
            for i, item in enumerate(dynamic_examples, 1):
                bad = item.get("bad", "")
                better = item.get("better", "")
                lines.append(f"{i}. BAD: {bad}")
                lines.append(f"   BETTER: {better}")
        return "\n".join(lines)

    def _build_guardrails_block(self, writer_fb: Dict[str, Any], scorer_feedback: Dict[str, Any], job_type: str) -> str:
        lines = [
            "SCORER GUIDANCE TO APPLY",
            f"- Top fixes: {json.dumps(scorer_feedback.get('top_fixes', []))}",
            f"- Wording gaps: {json.dumps(scorer_feedback.get('wording_gaps', []))}",
            f"- Skill gaps: {json.dumps(scorer_feedback.get('skill_gaps', []))}",
            f"- Core ownership areas: {json.dumps(writer_fb.get('core_ownership_areas', []))}",
            f"- Skills to emphasize in bullets: {json.dumps(writer_fb.get('skills_to_emphasize', []))}",
            f"- Skills that can stay mostly in Skills: {json.dumps(writer_fb.get('skills_ok_in_skills_only', []))}",
            f"- Bad patterns to avoid: {json.dumps(writer_fb.get('bad_patterns_to_avoid', []))}",
            f"- Summary guidance: {writer_fb.get('summary_guidance', '')}",
            "",
            "ITERATION RULES",
            "- Do not repeat the same mistakes from the scorer feedback.",
            "- If a previous version sounded too generic, rewrite with more object, workflow, and operational detail.",
            "- If a previous version sounded too inflated, reduce architect or governance claims to supported solution-level language.",
            "- If a previous version overused tool stacking, split the ideas into separate grounded bullets.",
        ]
        if job_type.lower() == "fulltime":
            lines += [
                "- Fulltime mode: selective emphasis is preferred over proving every optional JD skill.",
                "- Fulltime mode: do not force Java, CrewAI, Pydantic, or other replaceable tools deeply into work bullets unless truly supported.",
            ]
        else:
            lines += [
                "- Contract mode: broader coverage is acceptable if still believable.",
                "- Contract mode: you may mirror more JD items directly, but keep bullets readable and grounded.",
            ]
        return "\n".join(lines)

    def _parse_resume_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r'^```json?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("Failed to parse writer response as JSON.")


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
                {"bad": "Worked on AWS and LangChain for AI solutions.", "better": "Built LangChain-based retrieval workflows on AWS to support grounded document responses in production."}
            ],
            "summary_guidance": "Keep summary closer to systems and production actions."
        }
    }
    result = writer.generate_resume(test_jd, role_type="AI Engineer", job_type="Fulltime", scorer_feedback=scorer_feedback)
    print(json.dumps(result, indent=2)[:800] + "...")
