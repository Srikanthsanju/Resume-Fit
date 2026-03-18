from openai import OpenAI
import os
import json
from ..config import settings

class ScorerAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = settings.SCORER_MODEL

    def score_section(self, tag, generated_content, target_count, jd, job_type):
        # Skip strict scoring for basic text blocks
        if "description" in tag.lower() or "env" in tag.lower():
            return {"passed": True, "score": 100, "feedback": ""}

        actual_count = len(generated_content)
        content_text = "\n".join(generated_content)
        
        prompt = f"""
        Evaluate this generated resume section: [[{tag}]] for a {job_type} role.
        Target Bullets: {target_count} | Actual Bullets: {actual_count}
        JD: {jd}
        
        Content:\n{content_text}
        
        Rules:
        1. If it is a bulleted section and Actual is not within +/- {settings.BULLET_TOLERANCE} of Target, it FAILS automatically.
        2. Evaluate technical realism and JD keyword alignment.
        
        Return JSON ONLY:
        {{
            "passed": boolean,
            "score": integer (0-100),
            "feedback": "Specific instructions for the writer if failed, else empty"
        }}
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        
        return json.loads(response.choices[0].message.content)