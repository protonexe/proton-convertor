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
        # Use a more robust FFmpeg command. 
        # For audio targets, we specifically extract audio.
        # For video targets, we ensure compatibility.
        
        audio_exts = {"mp3", "wav", "ogg", "m4a", "flac", "aac", "opus"}
        
        if self._target_fmt.lower() in audio_exts:
            # Audio extraction: disable video stream
            cmd = ["ffmpeg", "-y", "-i", str(input_path), "-vn", str(output_path)]
        else:
            # Video conversion: ensure standard pixel format for maximum compatibility
            cmd = ["ffmpeg", "-y", "-i", str(input_path), "-pix_fmt", "yuv420p", str(output_path)]
            
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            # Log the actual ffmpeg stderr to the console for debugging
            print(f"FFmpeg Error: {e.stderr.decode()}")
            raise e
            
        return output_path

# Expanded list of media formats supported by FFmpeg
media_extensions = [
    "mp3", "wav", "ogg", "m4a", "flac", "aac", "mp4", "avi", "mkv", "mov", "wmv", "flv", "webm",
    "ts", "m4v", "3gp", "3gp2", "vob", "ogg", "opus"
]
registry.register_family("media", media_extensions)

for fmt in media_extensions:
    registry.register(MediaFamilyConverter(fmt))
