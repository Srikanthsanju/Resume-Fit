from .template_parser import TemplateParser
from .writer_agent import WriterAgent
from .scorer_agent import ScorerAgent
from .docx_generator import DocxGenerator
from ..config import settings
import json

class ResumeOrchestrator:
    def __init__(self):
        self.parser = TemplateParser()
        self.writer = WriterAgent()
        self.scorer = ScorerAgent()
        self.generator = DocxGenerator()

    def _get_target_count(self, tag, job_type):
        """Restoring your exact math for Fulltime vs Contract."""
        tag_lower = tag.lower()
        if "description" in tag_lower or "env" in tag_lower or "skills" in tag_lower:
            return 0
            
        counts = {
            "contract": {"summary": 13, "exp_1": 14, "exp_2": 14, "exp_3": 10, "exp_4": 9},
            "fulltime": {"summary": 5, "exp_1": 11, "exp_2": 10, "exp_3": 9, "exp_4": 7}
        }
        
        mode = job_type.lower()
        for key, count in counts.get(mode, {}).items():
            if key in tag_lower:
                return count
        return 5 

    def process_job(self, jd: str, job_type: str, company_name: str, job_title: str):
        template_path = settings.CONTRACT_TEMPLATE if job_type == "Contract" else settings.FULLTIME_TEMPLATE
        tags = self.parser.get_tags(template_path)
        
        # Build the strict mathematical blueprint for the Writer
        format_map = {tag: self._get_target_count(tag, job_type) for tag in tags}
        
        print(f"🚀 Starting GLOBAL Generation using template: {template_path.name}")
        
        print("✍️ Writer Agent is drafting the full narrative...")
        draft_resume = self.writer.generate_full_resume(tags, format_map, jd, job_type)
        
        print("🧐 Scorer Agent is reviewing the entire document...")
        evaluation = self.scorer.score_full_resume(draft_resume, format_map, jd, job_type)
        final_score = evaluation.get("final_score", 100)
        
        final_data = draft_resume
        if final_score < 90:
            print(f"⚠️ Score is {final_score}. Writer is applying Scorer's exact fixes...")
            final_data = self.writer.refine_full_resume(draft_resume, evaluation.get("feedback"), jd, job_type)

        output_filename = f"Srikanth_{company_name.replace(' ', '_')}_{job_type}.docx"
        output_path = settings.OUTPUT_DIR / output_filename
        self.generator.fill_template(template_path, output_path, final_data)
        
        print(f"\n🎉 Generation Complete! Final Score: {final_score}")
        
        return {
            "passed": final_score >= 90,
            "final_score": final_score,
            "iterations": 2 if final_score < 90 else 1,
            "docx_url": f"/files/{output_filename}",
            "pdf_url": None,
            "resume_content": final_data,
            "score_details": {
                "ats_confidence": "High" if final_score > 85 else "Medium",
                "top_fixes": evaluation.get("top_fixes", [])
            }
        }