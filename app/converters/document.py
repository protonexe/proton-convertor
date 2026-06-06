import markdown
import html2text
import pdfplumber
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.utils import simpleSplit
from pathlib import Path
from app.converters.base import BaseConverter
from app.core.registry_instance import registry
from docx import Document

class DocConverter(BaseConverter):
    def __init__(self, src: str, target: str):
        self._src = src
        self._target = target

    @property
    def source_format(self) -> str: return self._src
    @property
    def target_format(self) -> str: return self._target

    def _extract_text(self, input_path: Path) -> str:
        ext = input_path.suffix.lower()
        try:
            if ext == ".txt":
                return input_path.read_text(encoding='utf-8', errors='ignore')
            elif ext == ".md":
                return input_path.read_text(encoding='utf-8', errors='ignore')
            elif ext == ".html":
                return html2text.html2text(input_path.read_text(encoding='utf-8', errors='ignore'))
            elif ext == ".pdf":
                with pdfplumber.open(input_path) as pdf:
                    return "\\n".join(page.extract_text() or "" for page in pdf.pages)
            elif ext == ".docx":
                doc = Document(input_path)
                return "\\n".join([para.text for para in doc.paragraphs])
            return input_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return "Could not extract text from file."

    async def convert(self, input_path: Path, output_path: Path) -> Path:
        src, target = self._src.lower(), self._target.lower()
        content = self._extract_text(input_path)
        
        if target == "txt":
            output_path.write_text(content, encoding='utf-8')
        elif target == "md":
            output_path.write_text(content, encoding='utf-8')
        elif target == "html":
            output_path.write_text(markdown.markdown(content), encoding='utf-8')
        elif target == "pdf":
            c = canvas.Canvas(str(output_path), pagesize=LETTER)
            width, height = LETTER
            
            text_obj = c.beginText(40, height - 40)
            text_obj.setFont("Helvetica", 11)
            text_obj.setLeading(14)
            
            lines = content.split("\\n")
            for line in lines:
                wrapped_lines = simpleSplit(line, "Helvetica", 11, 520)
                for w_line in wrapped_lines:
                    if text_obj.getY() < 40: # Page break
                        c.drawText(text_obj)
                        c.showPage()
                        text_obj = c.beginText(40, height - 40)
                        text_obj.setFont("Helvetica", 11)
                        text_obj.setLeading(14)
                    text_obj.textLine(w_line)
            
            c.drawText(text_obj)
            c.save()
        return output_path

# Define supported formats including docx
doc_formats = ["txt", "md", "html", "pdf", "docx"]
for src in doc_formats:
    for target in doc_formats:
        if src != target:
            registry.register(DocConverter(src, target))
