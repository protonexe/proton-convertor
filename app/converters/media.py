import subprocess
from pathlib import Path
from app.converters.base import BaseConverter
from app.core.registry_instance import registry

class MediaFamilyConverter(BaseConverter):
    def __init__(self, target_fmt: str):
        self._target_fmt = target_fmt

    @property
    def source_format(self) -> str:
        return "media" # Registered as family

    @property
    def target_format(self) -> str:
        return self._target_fmt

    async def convert(self, input_path: Path, output_path: Path) -> Path:
        # FFmpeg is the universal tool for media
        cmd = ["ffmpeg", "-y", "-i", str(input_path), str(output_path)]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

# Expanded list of media formats supported by FFmpeg
media_extensions = [
    "mp3", "wav", "ogg", "m4a", "flac", "aac", "mp4", "avi", "mkv", "mov", "wmv", "flv", "webm",
    "ts", "m4v", "3gp", "3gp2", "vob", "ogg", "opus"
]
registry.register_family("media", media_extensions)

for fmt in media_extensions:
    registry.register(MediaFamilyConverter(fmt))
