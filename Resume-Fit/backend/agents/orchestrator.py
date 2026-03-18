"""
Orchestrator - Manages the writer-scorer feedback loop
- Limited to 2 iterations to save tokens
- Logs token usage
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .writer_agent import WriterAgent
from .scorer_agent import ScorerAgent


class ResumeOrchestrator:
    def __init__(self, anthropic_key: str = None, openai_key: str = None):
        self.writer = WriterAgent(api_key=anthropic_key)
        self.scorer = ScorerAgent(api_key=openai_key)
        
        self.min_score = int(os.getenv("MIN_SCORE", 85))
        self.max_iterations = int(os.getenv("MAX_ITERATIONS", 2))  # Reduced to 2
        
        self.history = []
        self.total_tokens = {"input": 0, "output": 0}
    
    def process_job(
        self,
        job_description: str,
        role_type: str = "AI Engineer",
        job_type: str = "Fulltime",
        company_name: str = None,
        job_title: str = None
    ) -> dict:
        """Process a job description and generate optimized resume."""
        
        print("\n" + "="*60)
        print("🚀 STARTING RESUME GENERATION")
        print("="*60)
        print(f"   Role: {role_type}")
        print(f"   Type: {job_type}")
        print(f"   Max iterations: {self.max_iterations}")
        
        # Reset token counter
        self.total_tokens = {"input": 0, "output": 0}
        
        # Step 1: Identify ownership areas
        print("\n📋 Identifying ownership areas from JD...")
        ownership_areas = self.writer._identify_ownership_areas(job_description)
        print(f"   Found {len(ownership_areas)} areas: {ownership_areas[:3]}...")
        
        # Initialize
        feedback = None
        resume_content = None
        final_score = None
        iteration = 0
        scorer_feedback = None
        
        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n{'─'*40}")
            print(f"📝 ITERATION {iteration}/{self.max_iterations}")
            print(f"{'─'*40}")
            
            # Step 2: Generate resume
            print("\n🤖 Claude is writing resume...")
            resume_content, writer_tokens = self.writer.generate_resume(
                job_description=job_description,
                feedback=feedback,
                role_type=role_type,
                job_type=job_type,
                scorer_feedback=scorer_feedback
            )
            
            # Track tokens
            self.total_tokens["input"] += writer_tokens.get("input", 0)
            self.total_tokens["output"] += writer_tokens.get("output", 0)
            
            # Normalize keys for compatibility
            resume_content = self._normalize_resume_keys(resume_content)
            
            # Log bullet counts
            bullet_counts = {
                "summary": len(resume_content.get("summary", [])),
                "experience_1": len(resume_content.get("experience_1", [])),
                "experience_2": len(resume_content.get("experience_2", [])),
                "experience_3": len(resume_content.get("experience_3", [])),
                "experience_4": len(resume_content.get("experience_4", []))
            }
            total_bullets = sum(bullet_counts.values())
            print(f"   Generated bullets: {bullet_counts}")
            print(f"   Total bullets: {total_bullets}")
            
            # Step 3: Score resume
            print("\n🔍 GPT-4 is scoring resume...")
            score_result = self.scorer.score_resume(job_description, resume_content, job_type)
            
            score = score_result.get("score", 0)
            passed = score_result.get("passed", False)
            
            print(f"   Score: {score}/100")
            print(f"   Status: {'✅ PASSED' if passed else '❌ NEEDS IMPROVEMENT'}")
            
            # Store in history
            self.history.append({
                "iteration": iteration,
                "score": score,
                "passed": passed,
                "bullet_counts": bullet_counts,
                "total_bullets": total_bullets,
                "ats_confidence": score_result.get("ats_confidence", "unknown"),
                "recruiter_confidence": score_result.get("recruiter_confidence", "unknown"),
            })
            
            # Check if passed
            if passed or score >= self.min_score:
                print(f"\n🎉 Resume passed with score {score}!")
                final_score = score_result
                break
            
            # Prepare feedback for next iteration
            if iteration < self.max_iterations:
                print("\n📋 Preparing feedback for next iteration...")
                feedback = self._build_feedback(score_result)
                scorer_feedback = score_result
            
            final_score = score_result
        
        # Ensure keys are normalized for DOCX generator
        resume_content = self._normalize_resume_keys(resume_content)
        
        # Final summary with token usage
        print("\n" + "="*60)
        print("📊 GENERATION COMPLETE")
        print("="*60)
        print(f"   Total iterations: {iteration}")
        print(f"   Final score: {final_score.get('score', 'N/A')}/100")
        print(f"   ATS Confidence: {final_score.get('ats_confidence', 'N/A')}")
        print(f"   Recruiter Confidence: {final_score.get('recruiter_confidence', 'N/A')}")
        print(f"   Status: {'✅ PASSED' if final_score.get('passed') else '⚠️ Best effort'}")
        print(f"\n💰 TOKEN USAGE:")
        print(f"   Input tokens: {self.total_tokens['input']:,}")
        print(f"   Output tokens: {self.total_tokens['output']:,}")
        print(f"   Estimated cost: ${self._estimate_cost():.4f}")
        
        return {
            "resume_content": resume_content,
            "score": final_score,
            "iterations": iteration,
            "history": self.history,
            "ownership_areas": ownership_areas,
            "token_usage": self.total_tokens,
            "metadata": {
                "role_type": role_type,
                "job_type": job_type,
                "company_name": company_name,
                "job_title": job_title,
                "generated_at": datetime.now().isoformat()
            }
        }
    
    def _estimate_cost(self) -> float:
        """Estimate API cost based on token usage."""
        # Claude Sonnet pricing (approximate)
        input_cost = self.total_tokens["input"] * 0.000003  # $3 per 1M input tokens
        output_cost = self.total_tokens["output"] * 0.000015  # $15 per 1M output tokens
        return input_cost + output_cost
    
    def _normalize_resume_keys(self, resume_content: dict) -> dict:
        """Ensure both old and new key formats exist for compatibility."""
        if not isinstance(resume_content, dict):
            return resume_content
            
        key_mapping = {
            "experience_1": "bee_data",
            "experience_2": "allied_health",
            "experience_3": "byjus",
            "experience_4": "cognizant"
        }
        
        for new_key, old_key in key_mapping.items():
            if resume_content.get(new_key) and not resume_content.get(old_key):
                resume_content[old_key] = resume_content[new_key]
            elif resume_content.get(old_key) and not resume_content.get(new_key):
                resume_content[new_key] = resume_content[old_key]
        
        return resume_content
    
    def _build_feedback(self, score_result: dict) -> str:
        """Build detailed feedback for the writer agent."""
        lines = []
        
        if score_result.get("top_fixes"):
            lines.append("## TOP FIXES REQUIRED")
            for fix in score_result["top_fixes"]:
                lines.append(f"- {fix}")
        
        if score_result.get("skill_gaps"):
            lines.append("\n## SKILL GAPS")
            for gap in score_result["skill_gaps"][:5]:
                lines.append(f"- {gap}")
        
        if score_result.get("wording_gaps"):
            lines.append("\n## WORDING ISSUES")
            for gap in score_result["wording_gaps"][:5]:
                lines.append(f"- {gap}")
        
        return "\n".join(lines)
    
    def print_score_breakdown(self, score_result: dict):
        """Print detailed score breakdown."""
        print("\n📈 SCORE BREAKDOWN:")
        
        if "breakdown" in score_result:
            for category, data in score_result["breakdown"].items():
                if isinstance(data, dict):
                    score = data.get("score", 0)
                    max_score = data.get("max", 10)
                    pct = (score / max_score * 100) if max_score > 0 else 0
                    bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                    print(f"   {category:25} [{bar}] {score}/{max_score}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    orchestrator = ResumeOrchestrator()
    
    test_jd = """
    Senior AI Engineer at TechCorp
    Requirements:
    - 5+ years of Python development
    - Experience building RAG architectures
    """
    
    result = orchestrator.process_job(
        job_description=test_jd,
        role_type="AI Engineer",
        job_type="Fulltime",
        company_name="TechCorp",
        job_title="Senior AI Engineer"
    )
