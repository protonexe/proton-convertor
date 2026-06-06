import base64
import json
from pathlib import Path
from typing import Any, Dict
from app.converters.base import BaseConverter
from app.core.registry_instance import registry
import os
import time

class Base64Converter(BaseConverter):
    def __init__(self):
        pass

    @property
    def source_format(self) -> str: return "any"
    @property
    def target_format(self) -> str: return "b64"

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
        with open(input_path, "rb") as f:
            encoded = base64.b64encode(f.read())
        output_path.write_text(encoded.decode('utf-8'), encoding='utf-8')
        return output_path

class HexDumpConverter(BaseConverter):
    def __init__(self):
        pass

    @property
    def source_format(self) -> str: return "any"
    @property
    def target_format(self) -> str: return "hex"

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
        with open(input_path, "rb") as f:
            data = f.read()
            hex_data = data.hex(' ')
        output_path.write_text(hex_data, encoding='utf-8')
        return output_path

class MetadataConverter(BaseConverter):
    def __init__(self):
        pass

    @property
    def source_format(self) -> str: return "any"
    @property
    def target_format(self) -> str: return "meta"

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
        stats = input_path.stat()
        metadata = {
            "filename": input_path.name,
            "size_bytes": stats.st_size,
            "created": time.ctime(stats.st_ctime),
            "modified": time.ctime(stats.st_mtime),
            "extension": input_path.suffix,
        }
        # Try to get more specific metadata if it's an image
        try:
            from PIL import Image
            with Image.open(input_path) as img:
                metadata["image_info"] = {
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                }
        except:
            pass
            
        output_path.write_text(json.dumps(metadata, indent=4), encoding='utf-8')
        return output_path

# Register as standard converters (Any -> X)
registry.register(Base64Converter())
registry.register(HexDumpConverter())
registry.register(MetadataConverter())
