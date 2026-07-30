import subprocess
from pathlib import Path
from PIL import Image
from app.converters.base import BaseConverter
from app.core.registry_instance import registry

class CompressionConverter(BaseConverter):
    def __init__(self, target_type: str):
        self._target_type = target_type  # "image", "video", "audio"

    @property
    def source_format(self) -> str:
        return self._target_type

    @property
    def target_format(self) -> str:
        return self._target_type

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
        options = options or {}
        level = options.get("level", "medium")  # "low", "medium", "high"

        if self._target_type == "image":
            with Image.open(input_path) as img:
                fmt = img.format if img.format else "JPEG"
                if fmt in ("RGBA", "PNG"):
                    img.save(output_path, format=fmt, optimize=True, quality=self._get_quality(level))
                else:
                    img.convert("RGB").save(output_path, format="JPEG", optimize=True, quality=self._get_quality(level))

        elif self._target_type == "video":
            crf = {"low": "18", "medium": "23", "high": "28"}.get(level, "23")
            cmd = ["ffmpeg", "-y", "-i", str(input_path), "-vcodec", "libx264", "-crf", crf, str(output_path)]
            subprocess.run(cmd, check=True, capture_output=True)

        elif self._target_type == "audio":
            bitrate = {"low": "128k", "medium": "192k", "high": "64k"}.get(level, "192k")
            cmd = ["ffmpeg", "-y", "-i", str(input_path), "-b:a", bitrate, str(output_path)]
            subprocess.run(cmd, check=True, capture_output=True)

        return output_path

    def _get_quality(self, level: str) -> int:
        return {"low": 90, "medium": 70, "high": 40}.get(level, 70)

# Register as tools only (not graph converters - they need specific file type inputs)
registry.register_tool("compress-image", CompressionConverter("image"))
registry.register_tool("compress-video", CompressionConverter("video"))
registry.register_tool("compress-audio", CompressionConverter("audio"))
