"""
Rulebook-driven writer agent

- Uses Anthropic for prose generation
- Reads job_type and role_type from caller
- Relies on guidelines for point counts and expansion behavior
- Consumes scorer feedback strongly
- Enforces explicit bullet counts per job type
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

    def _get_bullet_count_instructions(self, job_type: str) -> str:
        """Return explicit bullet count requirements based on job type."""
        if job_type.lower() == "contract":
            return """
MANDATORY BULLET COUNTS FOR CONTRACT MODE - YOU MUST FOLLOW THESE EXACTLY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• summary: EXACTLY 8 to 10 bullets (aim for 10)
• experience_1: EXACTLY 14 to 18 bullets (aim for 15)
• experience_2: EXACTLY 12 to 14 bullets (aim for 12)
• experience_3: EXACTLY 10 to 12 bullets (aim for 10)
• experience_4: EXACTLY 10 to 11 bullets (aim for 8)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONTRACT MODE EXPANSION RULES:
- This is a vendor-friendly resume requiring HIGH keyword density
- Generate MORE bullets by splitting complex ideas into multiple grounded bullets
- Each ownership area should have 2-3 bullets covering different angles
- Allow strategic repetition of core skills (RAG, LLM, AWS, orchestration, etc.)
- Longer bullets are acceptable when readable
- More platform-specific and architecture details are expected

DO NOT generate only 5-7 bullets per experience - that is FULLTIME mode.
CONTRACT MODE REQUIRES 2-3x MORE BULLETS than Fulltime.
"""
        else:  # Fulltime
            return """
MANDATORY BULLET COUNTS FOR FULLTIME MODE - YOU MUST FOLLOW THESE EXACTLY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• summary: EXACTLY 4 to 6 bullets
• experience_1: EXACTLY 9 bullets
• experience_2: EXACTLY 8 to 10 bullets
• experience_3: EXACTLY 7 to 10 bullets
• experience_4: EXACTLY 7 to 10 bullets (use only when relevant)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FULLTIME MODE RULES:
- Keep resume focused, selective, and realistic
- Prefer realism over maximum keyword density
- Do not force every JD skill into bullets
- Summary should feel selective and mature
"""

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
        bullet_count_instructions = self._get_bullet_count_instructions(job_type)

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

{bullet_count_instructions}

ROLE TYPE RULE
Follow the role-specific emphasis from the rulebook.
Do not force AI Engineer language if the role type is Data Scientist or Software Engineer.

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

FINAL CHECKLIST BEFORE RESPONDING:
1. Have I generated the CORRECT NUMBER of bullets for {job_type} mode?
2. For Contract: Did I generate 14-18 bullets for experience_1? 12-14 for experience_2? 10-12 for experience_3? 6-10 for experience_4? 8-10 for summary?
3. For Fulltime: Did I keep it to ~7 bullets for experience_1?
4. Are bullets grounded with object + action + system + result?
5. Did I avoid generic phrases like "strong experience" and "proven track record"?
"""

        user_prompt = f"""
JOB DESCRIPTION
{job_description}

"""
        if feedback:
            user_prompt += f"""ADDITIONAL FEEDBACK
{feedback}

"""
        user_prompt += f"""
Generate the resume now for {job_type.upper()} MODE.
Remember: {"Contract mode needs 14-18 bullets for experience_1, 12-14 for experience_2, etc." if job_type.lower() == "contract" else "Fulltime mode needs ~8 bullets for experience_1."}
Return only valid JSON.
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=12000,  # Increased for Contract mode
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
                "",
                "CONTRACT MODE REMINDERS:",
                "- Generate 14-18 bullets for experience_1 (NOT 5-7!)",
                "- Generate 12-14 bullets for experience_2",
                "- Generate 11-12 bullets for experience_3",
                "- Generate 10-11 bullets for experience_4",
                "- Generate 9-11 bullets for summary",
                "- Apply the Resume Expansion Algorithm from the rulebook.",
                "- Expand coverage, add architecture and operations detail.",
                "- Allow strategic repetition for vendor ATS.",
            ]
        else:
            lines += [
                "",
                "FULLTIME MODE REMINDERS:",
                "- Keep the resume selective, tighter, and more realistic.",
                "- Do not force every optional or replaceable JD tool into work bullets.",
                "- Generate ~7 bullets for experience_1, 5-6 bullets for experience_2/3, 4-6 bullets for summary, 5-6 bullets for experience_4",
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