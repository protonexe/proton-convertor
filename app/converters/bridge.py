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
        return "pdf"

    @property
    def target_format(self) -> str:
        return self._target

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
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
        return "image"

    @property
    def target_format(self) -> str:
        return self._target

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
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
        return "image"

    @property
    def target_format(self) -> str:
        return self._target

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
        temp_png = input_path.with_suffix(".temp.png")
        with Image.open(input_path) as img:
            img.convert("RGB").save(temp_png, "PNG")
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(temp_png), "-t", "1", "-pix_fmt", "yuv420p", str(output_path)]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        finally:
            if temp_png.exists():
                temp_png.unlink()
        return output_path


class MediaToImageConverter(BaseConverter):
    def __init__(self, target: str):
        self._target = target

    @property
    def source_format(self) -> str:
        return "media"

    @property
    def target_format(self) -> str:
        return self._target

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
        ffmpeg_fmt = "jpg" if self._target.lower() in ("jfif", "jpeg") else self._target
        temp_out = output_path.with_suffix(f".tmp.{ffmpeg_fmt}")
        cmd = ["ffmpeg", "-y", "-i", str(input_path), "-frames:v", "1", str(temp_out)]
        subprocess.run(cmd, check=True, capture_output=True)
        if temp_out != output_path:
            if output_path.exists():
                output_path.unlink()
            temp_out.rename(output_path)
        return output_path


class DocToDataConverter(BaseConverter):
    def __init__(self, target: str):
        self._target = target

    @property
    def source_format(self) -> str:
        return "doc"

    @property
    def target_format(self) -> str:
        return self._target

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
        text = input_path.read_text(encoding='utf-8', errors='ignore')
        import json
        if self._target == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({"content": text}, f)
        else:
            output_path.write_text(text, encoding='utf-8')
        return output_path


class DataToDocConverter(BaseConverter):
    def __init__(self, target: str):
        self._target = target

    @property
    def source_format(self) -> str:
        return "data"

    @property
    def target_format(self) -> str:
        return self._target

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
        import json, csv, yaml
        content = ""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                if input_path.suffix == ".json":
                    content = json.dumps(json.load(f), indent=2)
                elif input_path.suffix in [".yaml", ".yml"]:
                    content = yaml.dump(yaml.safe_load(f))
                else:
                    content = f.read()
        except Exception:
            content = "Data content"
        output_path.write_text(content, encoding='utf-8')
        return output_path


# Universal Connectivity Registration
# PDF -> Image formats
pdf_to_image_formats = ["png", "jpg", "jpeg", "webp", "bmp"]
for fmt in pdf_to_image_formats:
    registry.register(DocToImageConverter(fmt))

# Image -> Document formats (pdf, txt, md, html)
image_to_doc_formats = ["pdf", "txt", "md", "html"]
for fmt in image_to_doc_formats:
    registry.register(ImageToDocConverter(fmt))

# Image -> Media formats
media_formats = ["mp3", "wav", "ogg", "m4a", "flac", "aac", "mp4", "avi", "mkv", "mov", "wmv", "flv", "webm"]
for fmt in media_formats:
    registry.register(ImageToMediaConverter(fmt))

# Media -> Image formats
image_formats = ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif", "ico", "jfif"]
for fmt in image_formats:
    registry.register(MediaToImageConverter(fmt))

# Document -> Data formats
doc_formats = ["txt", "md", "html", "pdf"]
data_formats = ["json", "csv", "yaml", "yml", "xml", "xlsx", "xls"]
for fmt in data_formats:
    registry.register(DocToDataConverter(fmt))

# Data -> Document formats
for fmt in doc_formats:
    registry.register(DataToDocConverter(fmt))
