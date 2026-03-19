import anthropic
import os
import json
import re
from pathlib import Path
from ..config import settings

class WriterAgent:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = settings.WRITER_MODEL
        
        details_path = settings.CONFIG_DIR / "resume_details.md"
        rules_path = settings.TEMPLATE_DIR / "guidelines.md"
        self.details = details_path.read_text(encoding="utf-8") if details_path.exists() else ""
        self.rules = rules_path.read_text(encoding="utf-8") if rules_path.exists() else ""

    def _parse_json(self, text):
        """Robustly extracts JSON even if Claude wraps it in markdown blocks."""
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception as e:
                print(f"❌ JSON parsing failed inside regex: {e}")
        else:
            print("❌ Failed to find any JSON brackets in response.")
        return {}

    def generate_full_resume(self, tags, format_map, jd, job_type):
        format_instructions = ""
        for tag, count in format_map.items():
            if count == 0:
                if "description" in tag.lower():
                    format_instructions += f"- \"{tag}\": 2-3 sentences. MAX 70 words total. NO BULLETS.\n"
                elif "env" in tag.lower():
                    format_instructions += f"- \"{tag}\": Single comma-separated list starting with 'Environment: '.\n"
                elif "skills" in tag.lower():
                    format_instructions += f"- \"{tag}\": Key-Value format (e.g., 'Programming: Python'). One per line.\n"
            else:
                format_instructions += f"- \"{tag}\": EXACTLY {count} bullet points. 1-2 lines each. MUST start with an action verb.\n"

        system_prompt = f"""
        You are an elite-level Technical Resume Writer. 
        CRITICAL RULES:
        {self.rules}
        
        OUTPUT FORMAT: You MUST output ONLY valid JSON. The keys must match the exact tags requested (without brackets). 
        For bullets, output a list of strings. For descriptions/environments, output a list containing a single string.
        """

        user_prompt = f"""
        JOB TYPE: {job_type}
        JOB DESCRIPTION:\n{jd}\n
        MY EXPERIENCE:\n{self.details}\n
        
        DRAFT THE ENTIRE RESUME. Do not stuff keywords into pre-2022 jobs. Ensure a cohesive narrative across all jobs without sounding repetitive.
        
        CRITICAL FORMATTING BLUEPRINT (DO NOT DEVIATE):
        {format_instructions}
        """
        
        try:
            response = self.client.messages.create(
                model=self.model, max_tokens=4000, temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            raw_text = response.content[0].text.strip()
            return self._parse_json(raw_text)
        except Exception as e:
            print(f"❌ Generation API Error: {e}")
            return {}

    def refine_full_resume(self, draft_resume, feedback, jd, job_type):
        user_prompt = f"""
        Here is the current draft of the resume:\n{json.dumps(draft_resume)}\n
        The ATS Scorer found issues. Apply these EXACT fixes:\n{feedback}\n
        Return the ENTIRE updated JSON object using the exact same keys.
        """
        try:
            response = self.client.messages.create(
                model=self.model, max_tokens=4000, temperature=0.3,
                system=f"You are an elite-level Technical Resume Writer. Output ONLY valid JSON.\n{self.rules}",
                messages=[{"role": "user", "content": user_prompt}]
            )
            raw_text = response.content[0].text.strip()
            return self._parse_json(raw_text)
        except Exception as e:
            print(f"❌ Refinement API Error: {e}")
            return draft_resume