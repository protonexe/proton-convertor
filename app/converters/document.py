import markdown
import html2text
import pdfplumber
from reportlab.pdfgen import canvas
from pathlib import Path
from app.converters.base import BaseConverter
from app.core.registry_instance import registry

class DocConverter(BaseConverter):
    def __init__(self, src: str, target: str):
        self._src = src
        self._target = target

    @property
    def source_format(self) -> str: return self._src
    @property
    def target_format(self) -> str: return self._target

    async def convert(self, input_path: Path, output_path: Path) -> Path:
        src, target = self._src.lower(), self._target.lower()
        content = ""
        if src == "txt": content = input_path.read_text(encoding='utf-8')
        elif src == "md": content = input_path.read_text(encoding='utf-8')
        elif src == "html": content = html2text.html2text(input_path.read_text(encoding='utf-8'))
        elif src == "pdf":
            with pdfplumber.open(input_path) as pdf:
                content = "\\n".join(page.extract_text() or "" for page in pdf.pages)

        if target == "txt": output_path.write_text(content, encoding='utf-8')
        elif target == "md": output_path.write_text(content, encoding='utf-8')
        elif target == "html": output_path.write_text(markdown.markdown(content), encoding='utf-8')
        elif target == "pdf":
            c = canvas.Canvas(str(output_path))
            text_obj = c.beginText(40, 800); text_obj.setFont("Helvetica", 10)
            for line in content.split("\\n"): text_obj.textLine(line)
            c.drawText(text_obj); c.save()
        return output_path

# REGISTER FULL PAIRWISE for Docs
doc_formats = ["txt", "md", "html", "pdf"]
for src in doc_formats:
    for target in doc_formats:
        if src != target:
            registry.register(DocConverter(src, target))
