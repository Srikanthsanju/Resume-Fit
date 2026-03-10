"""
Writer Agent - Uses Claude to generate tailored resume content
"""

import os
import json
import re
from pathlib import Path
from typing import List, Optional

import anthropic


class WriterAgent:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        
        # Load config files
        config_dir = Path(__file__).parent.parent / "config"
        defaults_dir = Path(__file__).parent.parent / "defaults"
        
        # Load resume details
        self.resume_details = ""
        details_path = config_dir / "resume_details.md"
        if details_path.exists():
            self.resume_details = details_path.read_text(encoding="utf-8")
        
        # Load guidelines
        self.guidelines = ""
        guidelines_path = defaults_dir / "guidelines.md"
        if guidelines_path.exists():
            self.guidelines = guidelines_path.read_text(encoding="utf-8")
    
    def identify_ownership_areas(self, job_description: str) -> List[str]:
        """Extract 5-7 core ownership areas from the JD."""
        
        prompt = f"""Analyze this job description and extract 5-7 Core Technical Ownership Areas.

These are NOT tools. These are the real decisions and responsibilities the role owns end-to-end.

Examples of ownership areas:
- inference platform design
- retrieval architecture
- CI/CD for ML services
- model deployment and monitoring
- API service ownership
- data quality enforcement
- evaluation strategy

JOB DESCRIPTION:
{job_description}

Return ONLY a JSON array of ownership areas. Example:
["inference platform design", "RAG system architecture", "model evaluation framework"]
"""
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        text = response.content[0].text.strip()
        
        # Parse JSON
        try:
            # Find JSON array in response
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(text)
        except:
            # Fallback: split by newlines
            areas = [line.strip("- ").strip() for line in text.split("\n") if line.strip()]
            return areas[:7]
    
    def generate_resume(
        self,
        job_description: str,
        feedback: str = None,
        role_type: str = "AI Engineer",
        job_type: str = "Fulltime"
    ) -> dict:
        """
        Generate tailored resume content.
        
        Args:
            job_description: The job description to tailor for
            feedback: Optional feedback from scorer to incorporate
            role_type: "AI Engineer", "Data Scientist", or "Software Engineer"
            job_type: "Fulltime" or "Contract"
        
        Returns:
            dict with sections: summary, skills, bee_data, allied_health, byjus, cognizant
        """
        
        system_prompt = f"""You are an expert resume writer specializing in tech resumes for AI/ML roles.

## YOUR TASK
Generate tailored resume content for a job application. You must follow ALL the guidelines exactly.

## CANDIDATE'S BACKGROUND
{self.resume_details}

## RESUME WRITING GUIDELINES (FOLLOW EXACTLY)
{self.guidelines}

## ADDITIONAL CONTEXT
- Target Role Type: {role_type}
- Job Type: {job_type} ({"show wider skill range, be comprehensive" if job_type == "Fulltime" else "focus tightly on JD requirements, more technical depth"})

## OUTPUT FORMAT
Return a JSON object with these exact keys:
{{
    "summary": ["bullet 1", "bullet 2", ...],
    "skills": {{
        "Programming": "Python 3.11+, ...",
        "AI Frameworks": "LangChain, ...",
        // ... other categories ordered by JD priority
    }},
    "bee_data": ["bullet 1", "bullet 2", ...],
    "allied_health": ["bullet 1", "bullet 2", ...],
    "byjus": ["bullet 1", "bullet 2", ...],
    "cognizant": ["bullet 1", "bullet 2", ...]
}}

## CRITICAL RULES
1. Follow the character length distribution for each section per guidelines
2. Use verbatim phrases from the JD where natural
3. At least 60% of bullets must show ownership/decisions, not just tool usage
4. No phrase root should repeat more than once per section
5. Skills section order must mirror JD priority
6. AI content ONLY in Bee Data and Allied Health
7. ML content in BYJU'S, Software content in Cognizant
8. Around 70% of bullets should have metrics, 60% with specific numbers
9. Technologies are OR conditions - NEVER force AWS+Azure+GCP or Tableau+PowerBI together. Pick 1-2 naturally.
10. The resume must sound like a real engineer, not an AI keyword generator.
"""

        user_prompt = f"""## JOB DESCRIPTION
{job_description}

"""
        
        if feedback:
            user_prompt += f"""## FEEDBACK TO INCORPORATE
The ATS scorer provided this feedback. Address ALL issues:
{feedback}

"""
        
        user_prompt += """Generate the tailored resume content. Return ONLY valid JSON, no markdown."""
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            system=system_prompt
        )
        
        text = response.content[0].text.strip()
        
        # Parse JSON
        try:
            # Remove markdown code blocks if present
            if text.startswith("```"):
                text = re.sub(r'^```json?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)
            
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Try to find JSON object in response
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError(f"Failed to parse Claude response as JSON: {e}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    writer = WriterAgent()
    
    test_jd = """
    Senior AI Engineer at TechCorp
    
    Requirements:
    - 5+ years of Python development
    - Experience building RAG architectures
    - Proficiency with LangChain or similar frameworks
    - AWS deployment experience (SageMaker, EC2)
    """
    
    # Test ownership areas
    areas = writer.identify_ownership_areas(test_jd)
    print("Ownership Areas:", areas)
    
    # Test resume generation
    result = writer.generate_resume(test_jd, role_type="AI Engineer", job_type="Fulltime")
    print("\nGenerated Resume:")
    print(json.dumps(result, indent=2)[:500] + "...")
