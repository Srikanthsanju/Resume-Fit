import os
import json
from openai import OpenAI
from pathlib import Path
from ..config import settings

class ScorerAgent:
    def __init__(self):
        # Initializing the OpenAI client for GPT-4o
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = settings.SCORER_MODEL if hasattr(settings, 'SCORER_MODEL') else "gpt-4o"
        rules_path = settings.TEMPLATE_DIR / "guidelines.md"
        self.rules = rules_path.read_text(encoding="utf-8") if rules_path.exists() else ""

    def score_full_resume(self, draft_resume, format_map, jd, job_type):
        system_prompt = f"""
        You are a ruthless, highly technical ATS Scorer and Recruiter.
        You are grading an entire resume against the Job Description and these strict guidelines:
        {self.rules}
        
        Review the JSON draft. Look for:
        1. Repetition across jobs (Amnesia).
        2. Time-traveling AI (Generative AI/LLMs in jobs before 2022).
        3. Fluff, weak verbs, or violation of the 'OR Condition' (e.g., listing AWS, GCP, and Azure together).
        
        OUTPUT ONLY JSON:
        {{
            "final_score": <0-100 integer>,
            "feedback": "Detailed paragraph of what went wrong and EXACTLY how to rewrite the specific bad bullets.",
            "top_fixes": ["Fix 1", "Fix 2"]
        }}
        """

        user_prompt = f"JOB DESCRIPTION:\n{jd}\n\nRESUME DRAFT JSON:\n{json.dumps(draft_resume)}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                max_tokens=2000,
                response_format={ "type": "json_object" },
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            content = response.choices[0].message.content.strip()
            return json.loads(content)
            
        except Exception as e:
            print(f"Scoring Error: {e}")
            return {"final_score": 85, "feedback": "Could not parse scorer feedback.", "top_fixes": []}