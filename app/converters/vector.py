from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from pathlib import Path
from app.converters.base import BaseConverter
from app.core.registry_instance import registry

class SVGConverter(BaseConverter):
    def __init__(self, src: str, target: str):
        self._src = src
        self._target = target

    @property
    def source_format(self) -> str: return self._src
    @property
    def target_format(self) -> str: return self._target

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
        drawing = svg2rlg(str(input_path))
        
        if self._target == "png":
            renderPM.drawToFile(drawing, str(output_path), fmt="PNG")
        elif self._target == "pdf":
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(str(output_path))
            c.drawSaving(drawing)
            c.save()
        else:
            # Fallback
            renderPM.drawToFile(drawing, str(output_path), fmt="PNG")
            
        return output_path

registry.register(SVGConverter("svg", "png"))
registry.register(SVGConverter("svg", "pdf"))
