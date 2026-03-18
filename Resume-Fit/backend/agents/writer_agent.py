import anthropic
from openai import OpenAI
import os
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

    def _get_format_instructions(self, tag, target_count):
        """Changes the AI instructions based on the specific tag."""
        tag_lower = tag.lower()
        if "description" in tag_lower:
            return "FORMAT: Write a dense 3-4 sentence paragraph summarizing the role scope. NO BULLETS. DO NOT use line breaks."
        elif "env" in tag_lower:
            return "FORMAT: Write a single comma-separated list of technologies starting with 'Environment: '"
        elif "skills" in tag_lower:
            return "FORMAT: Write in Key-Value format (e.g., 'Programming: Python, SQL'). One category per line. NO BULLETS."
        else:
            return f"FORMAT: Write EXACTLY {target_count} bullet points. Each bullet should be 2-3 lines long. Return ONLY a list starting with dashes (-)."

    def generate_section(self, tag, target_count, jd, job_type, feedback=None):
        format_rules = self._get_format_instructions(tag, target_count)
        
        system_prompt = f"""
        You are an expert AI Resume Writer.
        {self.rules}
        
        TASK: Write ONLY the content for the [[{tag}]] section of a {job_type} resume.
        CRITICAL FORMAT CONSTRAINT: {format_rules}
        """
        
        user_prompt = f"""
        JOB DESCRIPTION:\n{jd}\n\n
        MY DEEP EXPERIENCE:\n{self.details}\n\n
        BRIDGE LOGIC: Use my experience to fulfill the format constraints. If a skill is in the JD but not my history, assume I used it to deploy or architect the systems in my existing projects.
        """
        
        if feedback:
            user_prompt += f"\n\nFIX THIS FEEDBACK: {feedback}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        text = response.content[0].text.strip()
        
        # If it's a bulleted section, parse it into a list. Otherwise, return the raw text.
        if "description" in tag.lower() or "env" in tag.lower():
            return [text] # Return as single-item list for consistency
        elif "skills" in tag.lower():
            return [line.strip() for line in text.split('\n') if line.strip()]
        else:
            return [line.strip("- •").strip() for line in text.split('\n') if line.strip()]