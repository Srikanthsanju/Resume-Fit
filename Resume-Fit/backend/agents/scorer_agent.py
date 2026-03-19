import anthropic
import os
import json
from pathlib import Path
from ..config import settings

class ScorerAgent:
    def __init__(self):
        # Using a fast, smart model for global scoring
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = settings.SCORER_MODEL if hasattr(settings, 'SCORER_MODEL') else "claude-3-haiku-20240307"
        rules_path = settings.TEMPLATE_DIR / "guidelines.md"
        self.rules = rules_path.read_text(encoding="utf-8") if rules_path.exists() else ""

    def score_full_resume(self, draft_resume, tags, jd, job_type):
        system_prompt = f"""
        You are a ruthless, highly technical ATS Scorer and Recruiter.
        You are grading an entire resume against the Job Description and these strict guidelines:
        {self.rules}
        
        Review the JSON draft. Look for:
        1. Repetition across jobs (Amnesia).
        2. Time-traveling AI (Generative AI/LLMs in jobs before 2022).
        3. Fluff, weak verbs, or violation of the 'OR Condition' (listing AWS, GCP, and Azure together).
        
        OUTPUT ONLY JSON:
        {{
            "final_score": <0-100>,
            "feedback": "Detailed paragraph of what went wrong and EXACTLY how to rewrite the specific bad bullets.",
            "top_fixes": ["Fix 1", "Fix 2"]
        }}
        """

        user_prompt = f"JOB DESCRIPTION:\n{jd}\n\nRESUME DRAFT JSON:\n{json.dumps(draft_resume)}"

        response = self.client.messages.create(
            model=self.model, max_tokens=2000, temperature=0.1,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        try:
            return json.loads(response.content[0].text.strip())
        except json.JSONDecodeError:
            return {"final_score": 85, "feedback": "Could not parse scorer feedback.", "top_fixes": []}