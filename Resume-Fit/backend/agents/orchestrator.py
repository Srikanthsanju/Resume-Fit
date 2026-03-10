"""
Orchestrator - Manages the writer-scorer feedback loop
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
        self.max_iterations = int(os.getenv("MAX_ITERATIONS", 3))
        
        self.history = []
    
    def process_job(
        self,
        job_description: str,
        role_type: str = "AI Engineer",
        job_type: str = "Fulltime",
        company_name: str = None,
        job_title: str = None
    ) -> dict:
        """
        Process a job description and generate optimized resume.
        
        Args:
            job_description: The full job description text
            role_type: "AI Engineer", "Data Scientist", or "Software Engineer"
            job_type: "Fulltime" or "Contract"
            company_name: Optional company name for file naming
            job_title: Optional job title for file naming
        
        Returns:
            dict with final resume content, score, and metadata
        """
        
        print("\n" + "="*60)
        print("🚀 STARTING RESUME GENERATION")
        print("="*60)
        print(f"   Role: {role_type}")
        print(f"   Type: {job_type}")
        
        # Step 1: Identify ownership areas
        print("\n📋 Identifying ownership areas from JD...")
        ownership_areas = self.writer.identify_ownership_areas(job_description)
        print(f"   Found {len(ownership_areas)} areas: {ownership_areas[:3]}...")
        
        # Initialize
        feedback = None
        resume_content = None
        final_score = None
        iteration = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n{'─'*40}")
            print(f"📝 ITERATION {iteration}/{self.max_iterations}")
            print(f"{'─'*40}")
            
            # Step 2: Generate resume
            print("\n🤖 Claude is writing resume...")
            resume_content = self.writer.generate_resume(
                job_description=job_description,
                feedback=feedback,
                role_type=role_type,
                job_type=job_type
            )
            
            bullet_counts = {
                "summary": len(resume_content.get("summary", [])),
                "bee_data": len(resume_content.get("bee_data", [])),
                "allied_health": len(resume_content.get("allied_health", [])),
                "byjus": len(resume_content.get("byjus", [])),
                "cognizant": len(resume_content.get("cognizant", []))
            }
            print(f"   Generated bullets: {bullet_counts}")
            
            # Step 3: Score resume
            print("\n🔍 GPT-4 is scoring resume...")
            score_result = self.scorer.score_resume(job_description, resume_content)
            
            score = score_result.get("score", 0)
            passed = score_result.get("passed", False)
            
            print(f"   Score: {score}/100")
            print(f"   Status: {'✅ PASSED' if passed else '❌ NEEDS IMPROVEMENT'}")
            
            # Store in history
            self.history.append({
                "iteration": iteration,
                "score": score,
                "passed": passed,
                "ats_confidence": score_result.get("ats_confidence", "unknown"),
                "recruiter_confidence": score_result.get("recruiter_confidence", "unknown"),
                "feedback_summary": score_result.get("top_fixes", [])[:3]
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
                print(f"   Feedback highlights:")
                for line in feedback.split("\n")[:5]:
                    if line.strip():
                        print(f"   {line}")
            
            final_score = score_result
        
        # Final summary
        print("\n" + "="*60)
        print("📊 GENERATION COMPLETE")
        print("="*60)
        print(f"   Total iterations: {iteration}")
        print(f"   Final score: {final_score.get('score', 'N/A')}/100")
        print(f"   ATS Confidence: {final_score.get('ats_confidence', 'N/A')}")
        print(f"   Recruiter Confidence: {final_score.get('recruiter_confidence', 'N/A')}")
        print(f"   Status: {'✅ PASSED' if final_score.get('passed') else '⚠️ Best effort'}")
        
        return {
            "resume_content": resume_content,
            "score": final_score,
            "iterations": iteration,
            "history": self.history,
            "ownership_areas": ownership_areas,
            "metadata": {
                "role_type": role_type,
                "job_type": job_type,
                "company_name": company_name,
                "job_title": job_title,
                "generated_at": datetime.now().isoformat()
            }
        }
    
    def _build_feedback(self, score_result: dict) -> str:
        """Build detailed feedback for the writer agent."""
        
        lines = []
        
        # Top fixes
        if score_result.get("top_fixes"):
            lines.append("## TOP FIXES REQUIRED")
            for fix in score_result["top_fixes"]:
                lines.append(f"- {fix}")
        
        # Skill gaps
        if score_result.get("skill_gaps"):
            lines.append("\n## SKILL GAPS")
            for gap in score_result["skill_gaps"][:5]:
                lines.append(f"- {gap}")
        
        # Wording gaps
        if score_result.get("wording_gaps"):
            lines.append("\n## WORDING ISSUES")
            for gap in score_result["wording_gaps"][:5]:
                lines.append(f"- {gap}")
        
        # Forced/generic signals
        if score_result.get("forced_or_generic_signals"):
            lines.append("\n## FORCED OR GENERIC SIGNALS")
            for signal in score_result["forced_or_generic_signals"][:5]:
                lines.append(f"- {signal}")
        
        # Evidence strength
        if score_result.get("evidence_strength"):
            evidence = score_result["evidence_strength"]
            if evidence.get("weak_or_missing"):
                lines.append("\n## WEAK OR MISSING EVIDENCE")
                for item in evidence["weak_or_missing"][:5]:
                    lines.append(f"- {item}")
        
        # Score breakdown
        if score_result.get("breakdown"):
            lines.append("\n## SCORE BREAKDOWN")
            for category, data in score_result["breakdown"].items():
                if isinstance(data, dict):
                    score = data.get("score", 0)
                    max_score = data.get("max", 10)
                    lines.append(f"- {category}: {score}/{max_score}")
        
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
        
        if score_result.get("strengths"):
            print("\n💪 STRENGTHS:")
            for s in score_result["strengths"][:3]:
                print(f"   ✓ {s}")
        
        if score_result.get("top_fixes"):
            print("\n⚠️ TOP FIXES:")
            for f in score_result["top_fixes"][:3]:
                print(f"   • {f}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    orchestrator = ResumeOrchestrator()
    
    test_jd = """
    Senior AI Engineer at TechCorp
    
    Requirements:
    - 5+ years of Python development
    - Experience building RAG architectures
    - Proficiency with LangChain or similar frameworks
    - AWS deployment experience (SageMaker, EC2)
    """
    
    result = orchestrator.process_job(
        job_description=test_jd,
        role_type="AI Engineer",
        job_type="Fulltime",
        company_name="TechCorp",
        job_title="Senior AI Engineer"
    )
    
    orchestrator.print_score_breakdown(result["score"])
