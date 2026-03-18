from docx import Document
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
import shutil

class DocxGenerator:
    def fill_template(self, template_path, output_path, final_data):
        shutil.copy(template_path, output_path)
        doc = Document(output_path)
        
        for tag, content_lines in final_data.items():
            for para in doc.paragraphs:
                if f"[[{tag}]]" in para.text:
                    # Clear the tag placeholder
                    para.text = para.text.replace(f"[[{tag}]]", "")
                    current_p = para._p
                    
                    # Insert content in reverse to maintain order when adding below the current paragraph
                    for line in reversed(content_lines):
                        new_p = OxmlElement("w:p")
                        current_p.addnext(new_p)
                        new_para = Paragraph(new_p, para._parent)
                        
                        # STYLE 1: Bullets
                        if "description" not in tag.lower() and "env" not in tag.lower() and "skills" not in tag.lower():
                            new_para.style = 'List Bullet'
                            new_para.add_run(line).font.name = "Times New Roman"
                            
                        # STYLE 2: Skills (Bold Key, Normal Value)
                        elif "skills" in tag.lower() and ":" in line:
                            category, skills = line.split(":", 1)
                            run_cat = new_para.add_run(category + ":")
                            run_cat.bold = True
                            run_cat.font.name = "Times New Roman"
                            new_para.add_run(skills).font.name = "Times New Roman"
                            
                        # STYLE 3: Standard Paragraphs (Description / Environment)
                        else:
                            run = new_para.add_run(line)
                            run.font.name = "Times New Roman"
                            if "env" in tag.lower() and line.startswith("Environment:"):
                                run.bold = True # Bold the 'Environment:' prefix
                                
        doc.save(output_path)
        return output_path
    