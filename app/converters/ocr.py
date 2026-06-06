import pytesseract
from pathlib import Path
from PIL import Image
from app.converters.base import BaseConverter
from app.core.registry_instance import registry

class OCRConverter(BaseConverter):
    def __init__(self, src: str, target: str):
        self._src = src
        self._target = target

    @property
    def source_format(self) -> str: return self._src
    @property
    def target_format(self) -> str: return self._target

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
        # Handle both images and PDFs (for PDFs, we'd need to convert pages to images first)
        # For simplicity, let's focus on Images -> Text/MD
        text = pytesseract.image_to_string(Image.open(input_path))
        
        output_path.write_text(text, encoding='utf-8')
        return output_path

# Register OCR paths: Any Image -> TXT or MD
image_formats = ["png", "jpg", "jpeg", "webp", "bmp", "tiff"]
for src in image_formats:
    for target in ["txt", "md"]:
        registry.register(OCRConverter(src, target))
