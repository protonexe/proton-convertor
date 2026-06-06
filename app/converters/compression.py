import subprocess
from pathlib import Path
from PIL import Image
from app.converters.base import BaseConverter
from app.core.registry_instance import registry

class CompressionConverter(BaseConverter):
    def __init__(self, target_type: str):
        self._target_type = target_type # "image", "video", "audio"

    @property
    def source_format(self) -> str: return "compression"
    @property
    def target_format(self) -> str: return "compressed"

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
        options = options or {}
        level = options.get("level", "medium") # "low", "medium", "high"
        
        if self._target_type == "image":
            with Image.open(input_path) as img:
                # Handle format
                fmt = img.format if img.format else "JPEG"
                if fmt == "RGBA" or fmt == "PNG":
                    # For PNGs, we optimize. For JPEGs, we use quality.
                    img.save(output_path, format=fmt, optimize=True, quality=self._get_quality(level))
                else:
                    img.convert("RGB").save(output_path, format="JPEG", optimize=True, quality=self._get_quality(level))
                    
        elif self._target_type == "video":
            # Use FFmpeg CRF (Constant Rate Factor)
            # 0 is lossless, 23 is default, 51 is worst quality
            crf = {"low": "18", "medium": "23", "high": "28"}.get(level, "23")
            cmd = ["ffmpeg", "-y", "-i", str(input_path), "-vcodec", "libx264", "-crf", crf, str(output_path)]
            subprocess.run(cmd, check=True, capture_output=True)
            
        elif self._target_type == "audio":
            # Use FFmpeg bitrate
            bitrate = {"low": "128k", "medium": "192k", "high": "64k"}.get(level, "192k")
            cmd = ["ffmpeg", "-y", "-i", str(input_path), "-b:a", bitrate, str(output_path)]
            subprocess.run(cmd, check=True, capture_output=True)
            
        return output_path

    def _get_quality(self, level: str) -> int:
        return {"low": 90, "medium": 70, "high": 40}.get(level, 70)

# Register compression tools
registry.register(CompressionConverter("image"))
registry.register(CompressionConverter("video"))
registry.register(CompressionConverter("audio"))

# Also register as tools
registry.register_tool("compress-image", CompressionConverter("image"))
registry.register_tool("compress-video", CompressionConverter("video"))
registry.register_tool("compress-audio", CompressionConverter("audio"))
