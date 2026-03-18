from docx import Document
import re

class TemplateParser:
    def get_tags(self, template_path):
        """Scans the document and returns a list of all tags found."""
        doc = Document(template_path)
        tags = []
        
        for para in doc.paragraphs:
            matches = re.findall(r'\[\[(.*?)\]\]', para.text)
            for match in matches:
                tag = match.strip()
                if tag not in tags:
                    tags.append(tag)
                    
        return tags