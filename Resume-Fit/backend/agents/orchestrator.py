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
        """Hardcoded targets based on your Gold Standard files."""
        tag_lower = tag.lower()
        if "description" in tag_lower or "env" in tag_lower or "skills" in tag_lower:
            return 0
            
        counts = {
            "contract": {"summary": 15, "exp_1": 11, "exp_2": 12, "exp_3": 10, "exp_4": 9},
            "fulltime": {"summary": 8, "exp_1": 7, "exp_2": 7, "exp_3": 8, "exp_4": 7}
        }
        
        mode = job_type.lower()
        for key, count in counts.get(mode, {}).items():
            if key in tag_lower:
                return count
        return 5 # Fallback default

    def process_job(self, jd: str, job_type: str, company_name: str, job_title: str):
        template_path = settings.CONTRACT_TEMPLATE if job_type == "Contract" else settings.FULLTIME_TEMPLATE
        tags = self.parser.get_tags(template_path)
        final_data = {}
        
        for tag in tags:
            target_count = self._get_target_count(tag, job_type)
            print(f"Generating [[{tag}]]...")
            
            content = self.writer.generate_section(tag, target_count, jd, job_type)
            result = self.scorer.score_section(tag, content, target_count, jd, job_type)
            
            if not result['passed']:
                print(f"Refining [[{tag}]] (Score: {result['score']})...")
                content = self.writer.generate_section(tag, target_count, jd, job_type, result['feedback'])
                
            final_data[tag] = content
            
        output_filename = f"Srikanth_{company_name.replace(' ', '_')}_{job_type}.docx"
        output_path = settings.OUTPUT_DIR / output_filename
        
        self.generator.fill_template(template_path, output_path, final_data)
        return {"download_url": f"/files/{output_filename}"}