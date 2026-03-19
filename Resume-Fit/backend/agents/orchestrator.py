from .template_parser import TemplateParser
from .writer_agent import WriterAgent
from .scorer_agent import ScorerAgent
from .docx_generator import DocxGenerator
from ..config import settings

class ResumeOrchestrator:
    def __init__(self):
        self.parser = TemplateParser()
        self.writer = WriterAgent()
        self.scorer = ScorerAgent()
        self.generator = DocxGenerator()

    def _get_target_count(self, tag, job_type):
        """
        Returns target bullet count based on tag type and job mode.
        Counts derived from reference resumes:
        - Fulltime (Srikanth_DA): Summary=8, Exp_1=12, Exp_2=10, Exp_3=9, Exp_4=7
        - Contract (Srikanth_BD): Summary=15, Exp_1=16, Exp_2=14, Exp_3=11, Exp_4=10
        """
        tag_lower = tag.lower()
        
        # Non-bullet sections return 0
        if "description" in tag_lower or "env" in tag_lower or "skills" in tag_lower:
            return 0
            
        counts = {
            "contract": {
                "summary": 15, 
                "exp_1": 16, 
                "exp_2": 14, 
                "exp_3": 11, 
                "exp_4": 10
            },
            "fulltime": {
                "summary": 8, 
                "exp_1": 12, 
                "exp_2": 10, 
                "exp_3": 9, 
                "exp_4": 7
            }
        }
        
        mode = job_type.lower()
        for key, count in counts.get(mode, {}).items():
            if key in tag_lower:
                return count
        return 5  # Fallback default

    def process_job(self, jd: str, job_type: str, company_name: str, job_title: str):
        template_path = settings.CONTRACT_TEMPLATE if job_type == "Contract" else settings.FULLTIME_TEMPLATE
        tags = self.parser.get_tags(template_path)
        final_data = {}
        
        # UI Tracking Variables
        total_iterations = 0
        avg_score = 0
        score_count = 0
        all_passed = True
        top_fixes = []

        print(f"🚀 Starting Atomic Generation using template: {template_path.name}")
        
        for tag in tags:
            target_count = self._get_target_count(tag, job_type)
            print(f"\n⚡ Processing Tag: [[{tag}]] | Target Bullets: {target_count} | Mode: {job_type}")
            
            # Generate
            content = self.writer.generate_section(tag, target_count, jd, job_type)
            total_iterations += 1
            
            # Score
            result = self.scorer.score_section(tag, content, target_count, jd, job_type)
            
            # Refine
            if not result.get('passed', True) and result.get('score', 100) != 100:
                print(f"⚠️ [[{tag}]] failed initial scoring (Score: {result.get('score')}). Refining...")
                content = self.writer.generate_section(tag, target_count, jd, job_type, result.get('feedback'))
                total_iterations += 1
                all_passed = False
                if result.get('feedback'):
                    top_fixes.append(f"[{tag}] {result['feedback']}")
                    
            score_count += 1
            avg_score += result.get('score', 100)
            final_data[tag] = content
            print(f"✅ Finished [[{tag}]]. Generated {len(content)} items.")
            
        final_score = int(avg_score / score_count) if score_count > 0 else 100
        output_filename = f"Srikanth_{company_name.replace(' ', '_')}_{job_type}.docx"
        output_path = settings.OUTPUT_DIR / output_filename
        
        self.generator.fill_template(template_path, output_path, final_data)
        
        print(f"\n🎉 Generation Complete! Final Score: {final_score}")
        
        # FIXED: Matches exactly what Generate.jsx is looking for
        return {
            "passed": all_passed,
            "final_score": final_score,
            "iterations": total_iterations,
            "docx_url": f"/files/{output_filename}",
            "pdf_url": None, # Add PDF logic later if needed
            "resume_content": final_data,
            "score_details": {
                "ats_confidence": "High" if final_score > 85 else "Medium",
                "recruiter_confidence": "High" if final_score > 85 else "Medium",
                "top_fixes": top_fixes
            }
        }