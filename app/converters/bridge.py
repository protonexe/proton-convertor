import fitz  # PyMuPDF
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
from app.converters.base import BaseConverter
from app.core.registry_instance import registry

class DocToImageConverter(BaseConverter):
    def __init__(self, target: str):
        self._target = target
    @property
    def source_format(self) -> str:
        return "doc" # Family Hub
    @property
    def target_format(self) -> str:
        return self._target
    async def convert(self, input_path: Path, output_path: Path) -> Path:
        if input_path.suffix.lower() == ".pdf":
            doc = fitz.open(input_path)
            page = doc.load_page(0)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img.save(output_path)
            doc.close()
        else:
            text = input_path.read_text(encoding='utf-8', errors='ignore')[:500]
            img = Image.new('RGB', (800, 600), color=(255, 255, 255))
            d = ImageDraw.Draw(img)
            d.text((10, 10), text, fill=(0, 0, 0))
            img.save(output_path)
        return output_path

class ImageToDocConverter(BaseConverter):
    def __init__(self, target: str):
        self._target = target
    @property
    def source_format(self) -> str:
        return "image" # Family Hub
    @property
    def target_format(self) -> str:
        return self._target
    async def convert(self, input_path: Path, output_path: Path) -> Path:
        if self._target == "pdf":
            with Image.open(input_path) as img:
                img.convert("RGB").save(output_path, "PDF")
        else:
            output_path.write_text(f"Image file: {input_path.name}", encoding='utf-8')
        return output_path

class ImageToMediaConverter(BaseConverter):
    def __init__(self, target: str):
        self._target = target
    @property
    def source_format(self) -> str:
        return "image" # Family Hub
    @property
    def target_format(self) -> str:
        return self._target
    async def convert(self, input_path: Path, output_path: Path) -> Path:
        temp_png = input_path.with_suffix(".temp.png")
        with Image.open(input_path) as img:
            img.convert("RGB").save(temp_png, "PNG")
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(temp_png), "-t", "1", "-pix_fmt", "yuv420p", str(output_path)]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        finally:
            if temp_png.exists(): temp_png.unlink()
        return output_path

class MediaToImageConverter(BaseConverter):
    def __init__(self, target: str):
        self._target = target
    @property
    def source_format(self) -> str:
        return "media" # Family Hub
    @property
    def target_format(self) -> str:
        return self._target
    async def convert(self, input_path: Path, output_path: Path) -> Path:
        cmd = ["ffmpeg", "-y", "-i", str(input_path), "-frames:v", "1", str(output_path)]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

class DocToDataConverter(BaseConverter):
    def __init__(self, target: str):
        self._target = target
    @property
    def source_format(self) -> str:
        return "doc" # Family Hub
    @property
    def target_format(self) -> str:
        return self._target
    async def convert(self, input_path: Path, output_path: Path) -> Path:
        text = input_path.read_text(encoding='utf-8', errors='ignore')
        import json
        if self._target == "json":
            with open(output_path, 'w', encoding='utf-8') as f: json.dump({"content": text}, f)
        else:
            output_path.write_text(text, encoding='utf-8')
        return output_path

class DataToDocConverter(BaseConverter):
    def __init__(self, target: str):
        self._target = target
    @property
    def source_format(self) -> str:
        return "data" # Family Hub
    @property
    def target_format(self) -> str:
        return self._target
    async def convert(self, input_path: Path, output_path: Path) -> Path:
        import json, csv, yaml
        content = ""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                if input_path.suffix == ".json": content = json.dumps(json.load(f), indent=2)
                elif input_path.suffix in [".yaml", ".yml"]: content = yaml.dump(yaml.safe_load(f))
                else: content = f.read()
        except: content = "Data content"
        output_path.write_text(content, encoding='utf-8')
        return output_path

# Universal Connectivity Registration
image_formats = ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif", "ico"]
media_formats = ["mp3", "wav", "ogg", "m4a", "flac", "aac", "mp4", "avi", "mkv", "mov", "wmv", "flv", "webm"]
doc_formats = ["txt", "md", "html", "pdf"]
data_formats = ["json", "csv", "yaml", "yml", "xml", "xlsx", "xls"]

for fmt in image_formats:
    registry.register(DocToImageConverter(fmt))
    registry.register(ImageToDocConverter(fmt))

for fmt in media_formats:
    registry.register(ImageToMediaConverter(fmt))

for fmt in image_formats:
    registry.register(MediaToImageConverter(fmt))

for fmt in doc_formats:
    registry.register(DocToDataConverter(fmt))

for fmt in data_formats:
    registry.register(DataToDocConverter(fmt))
