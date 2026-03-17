from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from pathlib import Path
from datetime import datetime
import os
import subprocess


class ResumeGenerator:
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir or os.getenv("OUTPUT_DIR", "./output"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.body_font = "Times New Roman"
        self.name_font = "Times New Roman"
        self.body_size = 10
        self.header_size = 11

        # Position grid
        self.section_left = 0.00
        self.content_left = 0.04
        self.bullet_left = 0.08
        self.bullet_text_left = 0.26

    def generate(
        self,
        resume_content: dict,
        company_name: str = None,
        job_title: str = None,
        mode: str = "Fulltime",
    ) -> tuple:
        doc = Document()

        self._setup_document(doc)
        self._set_default_styles(doc)

        self._add_name(doc, "SRIKANTH MANCHIMCHETTY")
        self._add_contact_line(doc)

        self._add_section_header(doc, "SUMMARY")
        for bullet in resume_content.get("summary", []):
            self._add_bullet_point(doc, bullet)

        self._add_section_header(doc, "TECHNICAL SKILLS")
        for category, skills in resume_content.get("skills", {}).items():
            self._add_skill_line(doc, category, skills)

        self._add_section_header(doc, "PROFESSIONAL EXPERIENCE")
        jobs = [
            {
                "key": "bee_data",
                "company": "Bee Data Technologies,",
                "location": "Atlanta, GA",
                "dates": "Oct 2025 - Current",
                "title": "AI Engineer",
                "description": "Design and implement GenAI solutions using Large Language Models building RAG architectures, developing Python APIs with FastAPI, and deploying models on AWS infrastructure.",
                "environment": "Python 3.11, FastAPI, LangChain, LangGraph, LlamaIndex, PyTorch, Hugging Face, AWS (SageMaker, EC2, EKS, RDS, S3), Kubeflow, MLflow, Apache Spark, Docker, Kubernetes, PostgreSQL, Pinecone, Git.",
            },
            {
                "key": "allied_health",
                "company": "Allied Health Agency,",
                "location": "Dallas, TX",
                "dates": "Aug 2023 - Oct 2025",
                "title": "AI/ML Engineer",
                "description": "Build ML-powered applications and data pipelines for healthcare operations. Develop Python APIs integrating AI models, implement RAG workflows for document search, and deploy services on AWS infrastructure.",
                "environment": "Python 3.11, FastAPI, LangChain, Scikit-learn, AWS (EC2, RDS, S3, Lambda), PostgreSQL, Pandas, Docker.",
            },
            {
                "key": "byjus",
                "company": "BYJU'S,",
                "location": "Bangalore, India",
                "dates": "Oct 2021 - Aug 2023",
                "title": "Data Engineer",
                "description": "Build ML models and analytics platforms for recruitment and business development. Develop predictive algorithms using Python and Scikit-learn, create data pipelines with PySpark, and implement dashboards.",
                "environment": "Python 3.8, Scikit-learn, XGBoost, PySpark, GCP (BigQuery, Dataproc, Cloud Functions), Power BI, Pandas, NumPy, Git.",
            },
            {
                "key": "cognizant",
                "company": "Cognizant Technology Solutions,",
                "location": "Bangalore, India",
                "dates": "Jun 2019 - Oct 2021",
                "title": "Program Analyst",
                "description": "Develop software solutions for Product Lifecycle Management systems and financial data automation for enterprise clients.",
                "environment": "Python 3.7, Pandas, openpyxl, JavaScript, SQL Server 2016, SSIS, T-SQL, Visual Studio, Git.",
            },
        ]
        for job in jobs:
            self._add_job_entry(doc, job, resume_content, mode)

        self._add_section_header(doc, "EDUCATION")
        self._add_education_entry(
            doc,
            university="University of North Texas",
            location="Dallas, TX",
            degree="Masters of Science in Advanced Data Analytics",
            dates="Aug 2023 - Dec 2024",
            coursework="Machine Learning, Large Data Visualization, LLM, Cloud Platforms for Data Engineering, Database Systems and SQL Programming",
        )
        self._add_education_entry(
            doc,
            university="Amrita University",
            location="Bangalore, India",
            degree="Bachelor of Technology in Computer Science Engineering",
            dates="Jun 2015 - May 2019",
            coursework="Data Structures and Algorithms, Database Management Systems and Software Engineering",
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if company_name and job_title:
            safe_company = "".join(c for c in company_name if c.isalnum() or c in " _-").strip().replace(" ", "_")
            safe_title = "".join(c for c in job_title if c.isalnum() or c in " _-").strip().replace(" ", "_")
            base_name = f"Srikanth_{safe_company}_{safe_title}_{timestamp}"
        elif company_name:
            safe_company = "".join(c for c in company_name if c.isalnum() or c in " _-").strip().replace(" ", "_")
            base_name = f"Srikanth_{safe_company}_{timestamp}"
        else:
            base_name = f"Srikanth_Resume_{timestamp}"

        docx_path = self.output_dir / f"{base_name}.docx"
        pdf_path = self.output_dir / f"{base_name}.pdf"
        doc.save(str(docx_path))

        pdf_created = self._convert_to_pdf(docx_path, pdf_path)
        return docx_path, (pdf_path if pdf_created else None)

    def _setup_document(self, doc: Document):
        for section in doc.sections:
            section.top_margin = Inches(0.42)
            section.bottom_margin = Inches(0.42)
            section.left_margin = Inches(0.48)
            section.right_margin = Inches(0.48)

    def _set_default_styles(self, doc: Document):
        normal = doc.styles["Normal"]
        normal.font.name = self.body_font
        normal.font.size = Pt(self.body_size)
        try:
            normal._element.rPr.rFonts.set(qn("w:eastAsia"), self.body_font)
        except Exception:
            pass

    def _content_width_inches(self, doc: Document) -> float:
        section = doc.sections[0]
        return float((section.page_width - section.left_margin - section.right_margin) / 914400)

    def _right_tab_position(self, doc: Document, inset: float = 0.02):
        return Inches(self._content_width_inches(doc) - inset)

    def _set_left_grid(self, para, left_inch: float):
        para.paragraph_format.left_indent = Inches(left_inch)
        para.paragraph_format.first_line_indent = Inches(0)

    def _add_name(self, doc: Document, name: str):
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.space_before = Pt(0)
        para.paragraph_format.space_after = Pt(2)
        run = para.add_run(name)
        run.bold = True
        run.font.name = self.name_font
        run.font.size = Pt(16)

    def _add_contact_line(self, doc: Document):
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.space_before = Pt(0)
        para.paragraph_format.space_after = Pt(7)

        left = para.add_run("mvss.1998@gmail.com  -  +1(940)703-0146  -  ")
        left.font.name = self.body_font
        left.font.size = Pt(10)

        self._add_hyperlink(para, "https://www.linkedin.com/in/srikanthmanchimchetty", "LinkedIn")

        middle = para.add_run("  -  Dallas, TX, USA  -  ")
        middle.font.name = self.body_font
        middle.font.size = Pt(10)

        self._add_hyperlink(para, "https://github.com/Srikanthsanju", "Github")

    def _add_hyperlink(self, paragraph, url, text):
        part = paragraph.part
        r_id = part.relate_to(
            url,
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
            is_external=True,
        )
        hyperlink = OxmlElement("w:hyperlink")
        hyperlink.set(qn("r:id"), r_id)

        new_run = OxmlElement("w:r")
        r_pr = OxmlElement("w:rPr")

        r_fonts = OxmlElement("w:rFonts")
        r_fonts.set(qn("w:ascii"), self.body_font)
        r_fonts.set(qn("w:hAnsi"), self.body_font)
        r_pr.append(r_fonts)

        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), "20")
        r_pr.append(sz)

        color = OxmlElement("w:color")
        color.set(qn("w:val"), "0563C1")
        r_pr.append(color)

        underline = OxmlElement("w:u")
        underline.set(qn("w:val"), "single")
        r_pr.append(underline)

        new_run.append(r_pr)

        t = OxmlElement("w:t")
        t.text = text
        new_run.append(t)

        hyperlink.append(new_run)
        paragraph._p.append(hyperlink)

    def _add_section_header(self, doc: Document, title: str):
        para = doc.add_paragraph()
        self._set_left_grid(para, self.section_left)
        para.paragraph_format.space_before = Pt(6)
        para.paragraph_format.space_after = Pt(2)
        para.paragraph_format.keep_with_next = True
        run = para.add_run(title)
        run.bold = True
        run.font.name = self.body_font
        run.font.size = Pt(self.header_size)

        p_pr = para._p.get_or_add_pPr()
        p_bdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "8")
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), "000000")
        p_bdr.append(bottom)
        p_pr.append(p_bdr)

    def _add_skill_line(self, doc: Document, category: str, skills: str):
        para = doc.add_paragraph()
        self._set_left_grid(para, self.content_left)
        para.paragraph_format.space_before = Pt(0)
        para.paragraph_format.space_after = Pt(0)
        para.paragraph_format.line_spacing = 1.0

        cat_run = para.add_run(f"{category}: ")
        cat_run.bold = True
        cat_run.font.name = self.body_font
        cat_run.font.size = Pt(10)

        skills_run = para.add_run(skills)
        skills_run.font.name = self.body_font
        skills_run.font.size = Pt(10)

    def _add_bullet_point(self, doc: Document, text: str):
        para = doc.add_paragraph()
        pf = para.paragraph_format
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.line_spacing = 1.0
        pf.left_indent = Inches(self.bullet_left)
        pf.first_line_indent = Inches(0)
        pf.tab_stops.clear_all()
        pf.tab_stops.add_tab_stop(Inches(self.bullet_text_left))

        bullet_run = para.add_run("•\t")
        bullet_run.font.name = self.body_font
        bullet_run.font.size = Pt(10)

        text_run = para.add_run(text)
        text_run.font.name = self.body_font
        text_run.font.size = Pt(10)

    def _add_job_entry(self, doc: Document, job: dict, resume_content: dict, mode: str):
        para = doc.add_paragraph()
        self._set_left_grid(para, self.content_left)
        pf = para.paragraph_format
        pf.space_before = Pt(6)
        pf.space_after = Pt(0)
        pf.keep_with_next = True
        pf.tab_stops.clear_all()
        pf.tab_stops.add_tab_stop(self._right_tab_position(doc), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.SPACES)

        company_run = para.add_run(f"{job['company']} ")
        company_run.bold = True
        company_run.font.name = self.body_font
        company_run.font.size = Pt(10)

        loc_run = para.add_run(job["location"])
        loc_run.font.name = self.body_font
        loc_run.font.size = Pt(10)

        date_run = para.add_run("\t" + job["dates"])
        date_run.font.name = self.body_font
        date_run.font.size = Pt(10)

        title_para = doc.add_paragraph()
        self._set_left_grid(title_para, self.content_left)
        title_pf = title_para.paragraph_format
        title_pf.space_before = Pt(0)
        title_pf.space_after = Pt(1)
        title_pf.keep_with_next = True

        title_run = title_para.add_run(job["title"])
        title_run.bold = True
        title_run.font.name = self.body_font
        title_run.font.size = Pt(10)

        if mode == "Contract":
            desc_para = doc.add_paragraph()
            self._set_left_grid(desc_para, self.content_left)
            desc_para.paragraph_format.space_before = Pt(0)
            desc_para.paragraph_format.space_after = Pt(2)
            desc_run = desc_para.add_run(job["description"])
            desc_run.font.name = self.body_font
            desc_run.font.size = Pt(10)

            resp_para = doc.add_paragraph()
            self._set_left_grid(resp_para, self.content_left)
            resp_para.paragraph_format.space_before = Pt(1)
            resp_para.paragraph_format.space_after = Pt(1)
            resp_run = resp_para.add_run("Responsibilities:")
            resp_run.bold = True
            resp_run.font.name = self.body_font
            resp_run.font.size = Pt(10)

        # Support both old and new key formats
        key = job["key"]
        key_mapping = {
            "bee_data": "experience_1",
            "allied_health": "experience_2",
            "byjus": "experience_3",
            "cognizant": "experience_4"
        }
        # Try old key first, then new key
        new_key = key_mapping.get(key, key)
        bullets = resume_content.get(key, []) or resume_content.get(new_key, [])
        
        for bullet in bullets:
            self._add_bullet_point(doc, bullet)

        if mode == "Contract":
            env_para = doc.add_paragraph()
            self._set_left_grid(env_para, self.content_left)
            env_para.paragraph_format.space_before = Pt(3)
            env_para.paragraph_format.space_after = Pt(2)
            env_label = env_para.add_run("Environment: ")
            env_label.bold = True
            env_label.font.name = self.body_font
            env_label.font.size = Pt(10)
            env_text = env_para.add_run(job["environment"])
            env_text.font.name = self.body_font
            env_text.font.size = Pt(10)

    def _add_education_entry(self, doc: Document, university: str, location: str, degree: str, dates: str, coursework: str):
        school_para = doc.add_paragraph()
        self._set_left_grid(school_para, self.content_left)
        school_pf = school_para.paragraph_format
        school_pf.space_before = Pt(5)
        school_pf.space_after = Pt(0)
        school_pf.keep_with_next = True
        school_pf.tab_stops.clear_all()
        school_pf.tab_stops.add_tab_stop(self._right_tab_position(doc), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.SPACES)

        uni_run = school_para.add_run(f"{university}, ")
        uni_run.bold = True
        uni_run.font.name = self.body_font
        uni_run.font.size = Pt(10)

        loc_run = school_para.add_run(location)
        loc_run.font.name = self.body_font
        loc_run.font.size = Pt(10)

        date_run = school_para.add_run("\t" + dates)
        date_run.font.name = self.body_font
        date_run.font.size = Pt(10)

        degree_para = doc.add_paragraph()
        self._set_left_grid(degree_para, self.content_left)
        degree_para.paragraph_format.space_before = Pt(0)
        degree_para.paragraph_format.space_after = Pt(0)
        degree_para.paragraph_format.keep_with_next = True
        degree_run = degree_para.add_run(degree)
        degree_run.font.name = self.body_font
        degree_run.font.size = Pt(10)

        cw_para = doc.add_paragraph()
        self._set_left_grid(cw_para, self.content_left)
        cw_para.paragraph_format.space_before = Pt(0)
        cw_para.paragraph_format.space_after = Pt(2)
        cw_label = cw_para.add_run("Coursework: ")
        cw_label.bold = True
        cw_label.font.name = self.body_font
        cw_label.font.size = Pt(10)
        cw_text = cw_para.add_run(coursework)
        cw_text.font.name = self.body_font
        cw_text.font.size = Pt(10)

    def _convert_to_pdf(self, docx_path: Path, pdf_path: Path) -> bool:
        try:
            from docx2pdf import convert
            convert(str(docx_path), str(pdf_path))
            return True
        except Exception:
            pass

        for cmd in ("libreoffice", "soffice"):
            try:
                subprocess.run(
                    [cmd, "--headless", "--convert-to", "pdf", "--outdir", str(self.output_dir), str(docx_path)],
                    check=True,
                    capture_output=True,
                )
                return pdf_path.exists()
            except Exception:
                continue
        return False


if __name__ == "__main__":
    generator = ResumeGenerator(output_dir="./output")

    test_content = {
        "summary": ["Test summary point 1", "Test summary point 2"],
        "skills": {"Programming": "Python, SQL"},
        "experience_1": ["Experience 1 point 1"],
        "experience_2": ["Experience 2 point 1"],
        "experience_3": ["Experience 3 point 1"],
        "experience_4": ["Experience 4 point 1"],
    }

    docx_path, pdf_path = generator.generate(test_content, "Test", "Role", "Fulltime")
    print(f"DOCX: {docx_path}")
    print(f"PDF: {pdf_path}")
