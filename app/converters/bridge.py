import fitz  # PyMuPDF
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
from app.converters.base import BaseConverter
from app.core.registry_instance import registry

class PdfToImageConverter(BaseConverter):
    def __init__(self, target: str): self._target = target
    @property
    def source_format(self) -> str: return "pdf"
    @property
    def target_format(self) -> str: return self._target
    async def convert(self, input_path: Path, output_path: Path) -> Path:
        doc = fitz.open(input_path)
        page = doc.load_page(0)
        pix = page.get_pixmap()
        pix.save(str(output_path))
        doc.close()
        return output_path

class ImageToPdfConverter(BaseConverter):
    def __init__(self, src: str): self._src = src
    @property
    def source_format(self) -> str: return self._src
    @property
    def target_format(self) -> str: return "pdf"
    async def convert(self, input_path: Path, output_path: Path) -> Path:
        with Image.open(input_path) as img:
            img.convert("RGB").save(output_path, "PDF")
        return output_path

class ImageToMediaConverter(BaseConverter):
    def __init__(self, target: str): self._target = target
    @property
    def source_format(self) -> str: return "image"
    @property
    def target_format(self) -> str: return self._target
    async def convert(self, input_path: Path, output_path: Path) -> Path:
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(input_path), "-t", "1", "-pix_fmt", "yuv420p", str(output_path)]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

class MediaToImageConverter(BaseConverter):
    def __init__(self, target: str): self._target = target
    @property
    def source_format(self) -> str: return "media"
    @property
    def target_format(self) -> str: return self._target
    async def convert(self, input_path: Path, output_path: Path) -> Path:
        cmd = ["ffmpeg", "-y", "-i", str(input_path), "-frames:v", "1", str(output_path)]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

class TextToImageConverter(BaseConverter):
    def __init__(self, target: str): self._target = target
    @property
    def source_format(self) -> str: return "doc"
    @property
    def target_format(self) -> str: return self._target
    async def convert(self, input_path: Path, output_path: Path) -> Path:
        text = input_path.read_text(encoding='utf-8', errors='ignore')[:500]
        img = Image.new('RGB', (800, 600), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((10, 10), text, fill=(0, 0, 0))
        img.save(output_path)
        return output_path

# Universal Connectivity
image_formats = ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif", "ico"]
media_formats = ["mp3", "wav", "ogg", "m4a", "flac", "aac", "mp4", "avi", "mkv", "mov", "wmv", "flv", "webm"]
doc_formats = ["txt", "md", "html", "pdf"]

for fmt in image_formats:
    registry.register(PdfToImageConverter(fmt))
    registry.register(ImageToPdfConverter(fmt))

for fmt in media_formats:
    registry.register(ImageToMediaConverter(fmt))
    registry.register(MediaToImageConverter(fmt))

for fmt in image_formats:
    registry.register(TextToImageConverter(fmt))
