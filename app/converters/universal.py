import base64
from pathlib import Path
from app.converters.base import BaseConverter
from app.core.registry_instance import registry

class UniversalFallbackConverter(BaseConverter):
    """
    The 'Omega' converter. It handles any extension not registered
    by treating it as either a UTF-8 text file or a Binary Base64 stream.
    This ensures that NO file is ever 'unconvertible'.
    """
    @property
    def source_format(self) -> str:
        return "*" # Wildcard

    @property
    def target_format(self) -> str:
        return "txt" # Route everything to the Text Hub

    async def convert(self, input_path: Path, output_path: Path) -> Path:
        try:
            # Attempt to read as UTF-8 text
            content = input_path.read_text(encoding='utf-8')
            header = f"--- DETECTED TEXT FORMAT ({input_path.suffix}) ---\\n"
        except (UnicodeDecodeError, Exception):
            # Fallback to Binary -> Base64 string
            with open(input_path, 'rb') as f:
                binary_data = f.read()
                encoded = base64.b64encode(binary_data).decode('utf-8')
                header = f"--- DETECTED BINARY FORMAT ({input_path.suffix}) - BASE64 ENCODED ---\\n"
                content = encoded
        
        output_path.write_text(header + content, encoding='utf-8')
        return output_path

# Register as the global fallback
registry.set_fallback(UniversalFallbackConverter())
