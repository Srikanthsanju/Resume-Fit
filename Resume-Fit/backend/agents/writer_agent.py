"""
Writer agent with reference-based bullet counts and token logging

- Uses exact bullet counts from actual reference resumes
- Logs input/output tokens for cost tracking
- Fulltime: ~37 bullets total
- Contract: ~57 bullets total
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

    def _get_bullet_requirements(self, job_type: str) -> dict:
        """Return exact bullet counts based on reference resumes."""
        if job_type.lower() == "contract":
            return {
                "summary": 15,
                "experience_1": 11,
                "experience_2": 12,
                "experience_3": 10,
                "experience_4": 9,
                "total": 57
            }
        else:  # Fulltime
            return {
                "summary": 8,
                "experience_1": 7,
                "experience_2": 7,
                "experience_3": 8,
                "experience_4": 7,
                "total": 37
            }

    def generate_resume(
        self,
        job_description: str,
        feedback: Optional[str] = None,
        role_type: str = "AI Engineer",
        job_type: str = "Fulltime",
        scorer_feedback: Optional[Dict[str, Any]] = None
    ) -> Tuple[dict, dict]:
        """Generate resume and return (content, token_usage)."""
        
        scorer_feedback = self._normalize_scorer_feedback(scorer_feedback or {})
        ownership_areas = scorer_feedback["writer_feedback"].get("core_ownership_areas") or self._identify_ownership_areas(job_description)
        
        reqs = self._get_bullet_requirements(job_type)
        
        # Build the prompt with exact requirements
        system_prompt = self._build_system_prompt(job_type, role_type, reqs, ownership_areas, scorer_feedback)
        user_prompt = self._build_user_prompt(job_description, job_type, reqs, feedback)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Extract token usage
        token_usage = {
            "input": response.usage.input_tokens if hasattr(response, 'usage') else 0,
            "output": response.usage.output_tokens if hasattr(response, 'usage') else 0
        }
        
        print(f"   📊 Tokens - Input: {token_usage['input']:,}, Output: {token_usage['output']:,}")

        text = response.content[0].text.strip()
        result = self._parse_resume_json(text)
        
        # Validate and log bullet counts
        self._validate_bullet_counts(result, reqs, job_type)
        
        return result, token_usage

    def _build_system_prompt(self, job_type: str, role_type: str, reqs: dict, ownership_areas: list, scorer_feedback: dict) -> str:
        """Build system prompt with exact bullet count requirements."""
        
        bullet_table = f"""
┌─────────────────────────────────────────────────────────────┐
│  {job_type.upper()} MODE - EXACT BULLET COUNTS REQUIRED:              │
├─────────────────────────────────────────────────────────────┤
│  summary:      EXACTLY {reqs['summary']:2d} bullets                          │
│  experience_1: EXACTLY {reqs['experience_1']:2d} bullets                          │
│  experience_2: EXACTLY {reqs['experience_2']:2d} bullets                          │
│  experience_3: EXACTLY {reqs['experience_3']:2d} bullets                          │
│  experience_4: EXACTLY {reqs['experience_4']:2d} bullets                          │
├─────────────────────────────────────────────────────────────┤
│  TOTAL:        EXACTLY {reqs['total']:2d} bullets                          │
└─────────────────────────────────────────────────────────────┘
"""

        format_rules = ""
        if job_type.lower() == "contract":
            format_rules = """
CONTRACT MODE FORMAT:
- Include Description paragraph before Responsibilities for each experience
- Include Environment line after bullets listing all technologies
- Higher keyword density - strategic repetition allowed
- Longer, more detailed bullets acceptable
- More technical depth expected
"""
        else:
            format_rules = """
FULLTIME MODE FORMAT:
- Include Description paragraph before Responsibilities
- Include Environment line after bullets
- More focused and selective
- Avoid excessive keyword stuffing
- Quality over quantity
"""

        scorer_guidance = ""
        if scorer_feedback.get("top_fixes"):
            scorer_guidance = f"\nSCORER FEEDBACK TO ADDRESS:\n- " + "\n- ".join(scorer_feedback["top_fixes"][:5])

        return f"""You are an expert resume writer. Generate EXACTLY the number of bullets specified.

{bullet_table}

{format_rules}

CANDIDATE BACKGROUND:
{self.resume_details}

CONTEXT:
- Role type: {role_type}
- Job type: {job_type}
- Ownership areas: {json.dumps(ownership_areas)}
{scorer_guidance}

BULLET QUALITY RULES:
- Each bullet: object/data + action + system/tool + result
- Avoid: "responsible for", "worked on", "strong experience"
- Be specific and grounded

OUTPUT FORMAT - Return ONLY valid JSON:
{{
  "summary": ["{reqs['summary']} bullets here"],
  "skills": {{"Programming": "...", "AI Frameworks": "...", ...}},
  "experience_1": ["{reqs['experience_1']} bullets here"],
  "experience_2": ["{reqs['experience_2']} bullets here"],
  "experience_3": ["{reqs['experience_3']} bullets here"],
  "experience_4": ["{reqs['experience_4']} bullets here"]
}}

CRITICAL: Count your bullets! You MUST generate exactly {reqs['total']} total bullets."""

    def _build_user_prompt(self, job_description: str, job_type: str, reqs: dict, feedback: Optional[str]) -> str:
        """Build user prompt."""
        prompt = f"""JOB DESCRIPTION:
{job_description}

"""
        if feedback:
            prompt += f"""FEEDBACK FROM PREVIOUS ITERATION:
{feedback}

"""
        prompt += f"""Generate a {job_type.upper()} resume with EXACTLY these bullet counts:
- summary: {reqs['summary']} bullets
- experience_1: {reqs['experience_1']} bullets  
- experience_2: {reqs['experience_2']} bullets
- experience_3: {reqs['experience_3']} bullets
- experience_4: {reqs['experience_4']} bullets
- TOTAL: {reqs['total']} bullets

Return ONLY valid JSON. Count your bullets before responding."""
        
        return prompt

    def _validate_bullet_counts(self, result: dict, reqs: dict, job_type: str):
        """Validate and log actual vs required bullet counts."""
        actual = {
            "summary": len(result.get("summary", [])),
            "experience_1": len(result.get("experience_1", [])),
            "experience_2": len(result.get("experience_2", [])),
            "experience_3": len(result.get("experience_3", [])),
            "experience_4": len(result.get("experience_4", [])),
        }
        actual["total"] = sum(actual.values())
        
        print(f"\n   📋 Bullet Count Validation ({job_type}):")
        all_match = True
        for key in ["summary", "experience_1", "experience_2", "experience_3", "experience_4"]:
            match = "✓" if actual[key] == reqs[key] else "✗"
            if actual[key] != reqs[key]:
                all_match = False
            print(f"      {key}: {actual[key]}/{reqs[key]} {match}")
        
        total_match = "✓" if actual["total"] == reqs["total"] else "✗"
        print(f"      TOTAL: {actual['total']}/{reqs['total']} {total_match}")
        
        if not all_match:
            print(f"      ⚠️ Bullet counts don't match requirements!")

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

        for key in ["top_fixes", "wording_gaps", "skill_gaps"]:
            if not isinstance(merged.get(key), list):
                merged[key] = []

        wf = merged.get("writer_feedback")
        if not isinstance(wf, dict):
            wf = {}
        final_wf = dict(defaults["writer_feedback"])
        final_wf.update({k: v for k, v in wf.items() if v is not None})
        merged["writer_feedback"] = final_wf
        return merged

    def _identify_ownership_areas(self, job_description: str) -> List[str]:
        prompt = f"""Extract 5-8 core technical ownership areas from this JD.
Return only a JSON array of strings.

JOB DESCRIPTION:
{job_description}"""

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
