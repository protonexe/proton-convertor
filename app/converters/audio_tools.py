from pathlib import Path
from typing import List
from pydub import AudioSegment
from app.converters.base import BaseConverter
from app.core.registry_instance import registry

class AudioToolConverter(BaseConverter):
    def __init__(self, action: str):
        self._action = action

    @property
    def source_format(self) -> str: return "media"
    @property
    def target_format(self) -> str: return "media"

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
        # Input can be any media format supported by pydub
        audio = AudioSegment.from_file(str(input_path))
        
        if self._action == "trim":
            # Expects options['start_ms'], options['end_ms']
            start = options.get("start_ms", 0)
            end = options.get("end_ms", len(audio))
            audio = audio[start:end]
            
        elif self._action == "merge":
            # Expects options['files'] list
            files = options.get("files", [])
            combined = AudioSegment.empty()
            for f in files:
                combined += AudioSegment.from_file(f)
            audio = combined
            
        elif self._action == "volume":
            # Expects options['gain'] in dB
            gain = options.get("gain", 0)
            audio = audio + gain
            
        # Export using the target format extension
        fmt = output_path.suffix[1:].lower()
        audio.export(str(output_path), format=fmt)
        
        return output_path

registry.register(AudioToolConverter("trim"))
registry.register(AudioToolConverter("merge"))
registry.register(AudioToolConverter("volume"))
