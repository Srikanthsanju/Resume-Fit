"""
Rulebook-driven writer agent

- Uses Anthropic for prose generation
- Reads job_type and role_type from caller
- Relies on guidelines for point counts and expansion behavior
- Consumes scorer feedback strongly
- Avoids hardcoding personal section names in the prompt
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
        rp = config_dir / "resume_details.md"
        if rp.exists():
            self.resume_details = rp.read_text(encoding="utf-8")

        self.guidelines = ""
        gp = defaults_dir / "guidelines.md"
        if gp.exists():
            self.guidelines = gp.read_text(encoding="utf-8")

    def generate_resume(
        self,
        job_description: str,
        feedback: Optional[str] = None,
        role_type: str = "AI Engineer",
        job_type: str = "Fulltime",
        scorer_feedback: Optional[Dict[str, Any]] = None
    ) -> dict:
        scorer_feedback = self._normalize_scorer_feedback(scorer_feedback or {})
        ownership_areas = scorer_feedback["writer_feedback"].get("core_ownership_areas") or self._identify_ownership_areas(job_description)

        examples_block = self._examples_block(scorer_feedback["writer_feedback"])
        scorer_block = self._scorer_block(scorer_feedback, job_type)

        system_prompt = f"""
You are an expert resume writer.

You must write a resume that:
- scores higher in ATS
- follows the rulebook exactly
- aligns to the chosen role type and job type
- improves based on scorer feedback
- does not sound fake, inflated, or AI-generated

CANDIDATE BACKGROUND
{self.resume_details}

RULEBOOK
{self.guidelines}

CONTEXT
- Role type: {role_type}
- Job type: {job_type}
- Core ownership areas: {json.dumps(ownership_areas)}

ROLE TYPE RULE
Follow the role-specific emphasis from the rulebook.
Do not force AI Engineer language if the role type is Data Scientist or Software Engineer.

JOB TYPE RULE
Follow the job-type rules from the rulebook exactly.
Contract mode must expand density and depth.
Fulltime mode must stay more selective and concise.

{examples_block}

{scorer_block}

OUTPUT FORMAT
Return ONLY valid JSON with these exact keys:
{{
  "summary": ["bullet 1", "bullet 2", "..."],
  "skills": {{
    "Programming": "Python 3.11+, ..."
  }},
  "experience_1": ["bullet 1", "bullet 2", "..."],
  "experience_2": ["bullet 1", "bullet 2", "..."],
  "experience_3": ["bullet 1", "bullet 2", "..."],
  "experience_4": ["bullet 1", "bullet 2", "..."]
}}

CRITICAL RULES
- Use the rulebook point counts for the chosen job type
- Contract mode must apply the Resume Expansion Algorithm from the rulebook
- Fulltime mode must stay selective
- Do not force every optional or replaceable JD skill into bullets
- Keep some granular or replaceable skills mainly in Skills if the scorer allows it
- Prefer bullets with object or data + action + system + result
- Avoid generic phrases like strong experience, proven track record, demonstrated ability, and deep expertise
- Do not include metrics in the summary
"""

        user_prompt = f"""
JOB DESCRIPTION
{job_description}

"""
        if feedback:
            user_prompt += f"""ADDITIONAL FEEDBACK
{feedback}

"""
        user_prompt += "Generate the resume now. Return only valid JSON."

        response = self.client.messages.create(
            model=self.model,
            max_tokens=9000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = response.content[0].text.strip()
        return self._parse_resume_json(text)

    def _normalize_scorer_feedback(self, scorer_feedback: Dict[str, Any]) -> Dict[str, Any]:
        defaults = {
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
        prompt = f"""Extract 5 to 8 core technical ownership areas from this JD.

These are responsibilities, not tools.

Return only a JSON array.

JOB DESCRIPTION
{job_description}
"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        try:
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(text)
        except Exception:
            return [line.strip("- ").strip() for line in text.split("\n") if line.strip()][:8]

    def _examples_block(self, writer_feedback: Dict[str, Any]) -> str:
        dynamic = writer_feedback.get("rewrite_examples", [])

        lines = [
            "GOOD BULLET EXAMPLES",
            "1. Built SageMaker training and deployment workflows for batch and real-time inference, then tracked model versions to support controlled releases.",
            "2. Processed call transcripts and policy documents to generate features used by classification and retrieval models across support workflows.",
            "3. Implemented monitoring for drift and response quality, then triggered retraining jobs when service thresholds were breached.",
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
            "- name the object or data",
            "- name the action",
            "- name the system or platform",
            "- name the result",
        ]

        if dynamic:
            lines.append("")
            lines.append("SCORER-SPECIFIC REWRITE EXAMPLES")
            for i, item in enumerate(dynamic, 1):
                lines.append(f"{i}. BAD: {item.get('bad', '')}")
                lines.append(f"   BETTER: {item.get('better', '')}")

        return "\n".join(lines)

    def _scorer_block(self, scorer_feedback: Dict[str, Any], job_type: str) -> str:
        wf = scorer_feedback["writer_feedback"]
        lines = [
            "SCORER GUIDANCE TO APPLY",
            f"- Top fixes: {json.dumps(scorer_feedback.get('top_fixes', []))}",
            f"- Wording gaps: {json.dumps(scorer_feedback.get('wording_gaps', []))}",
            f"- Skill gaps: {json.dumps(scorer_feedback.get('skill_gaps', []))}",
            f"- Core ownership areas: {json.dumps(wf.get('core_ownership_areas', []))}",
            f"- Skills to emphasize in bullets: {json.dumps(wf.get('skills_to_emphasize', []))}",
            f"- Skills okay mainly in Skills: {json.dumps(wf.get('skills_ok_in_skills_only', []))}",
            f"- Bad patterns to avoid: {json.dumps(wf.get('bad_patterns_to_avoid', []))}",
            f"- Summary guidance: {wf.get('summary_guidance', '')}",
            "",
            "ITERATION RULES",
            "- Do not repeat the same weak patterns from prior iterations.",
            "- If scorer says bullets are vague, rewrite with more object, workflow, and operational detail.",
            "- If scorer says bullets are overloaded, split the ideas into separate grounded bullets.",
            "- If scorer says claims are too inflated, reduce them to supported solution-level language.",
        ]
        if job_type.lower() == "contract":
            lines += [
                "- Contract mode: apply the Resume Expansion Algorithm from the rulebook.",
                "- Contract mode: expand coverage, add architecture and operations detail, and allow strategic repetition for vendor ATS.",
            ]
        else:
            lines += [
                "- Fulltime mode: keep the resume selective, tighter, and more realistic.",
                "- Fulltime mode: do not force every optional or replaceable JD tool into work bullets.",
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
        except Exception:
            pass
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("Failed to parse writer response as JSON.")