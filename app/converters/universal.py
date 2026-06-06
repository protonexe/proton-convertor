import base64
import binascii
from pathlib import Path
from app.converters.base import BaseConverter
from app.core.registry_instance import registry

class UniversalFallbackConverter(BaseConverter):
    """
    The 'Omega' converter. It handles any extension not registered
    by treating it as either a UTF-8 text file or a Binary stream.
    """
    @property
    def source_format(self) -> str:
        return "*" # Wildcard

    @property
    def target_format(self) -> str:
        return "txt" # Route everything to the Text Hub

    def _is_binary(self, file_path: Path) -> bool:
        """Detects if a file is binary by checking for null bytes in the first 1024 bytes."""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\x00' in chunk
        except Exception:
            return True

    async def convert(self, input_path: Path, output_path: Path) -> Path:
        suffix = input_path.suffix or "no_extension"
        
        if not self._is_binary(input_path):
            try:
                content = input_path.read_text(encoding='utf-8')
                header = f"--- DETECTED TEXT FORMAT ({suffix}) ---\n"
            except UnicodeDecodeError:
                # Fallback to binary if UTF-8 fails despite null-byte check
                return await self._convert_binary(input_path, output_path, suffix)
        else:
            return await self._convert_binary(input_path, output_path, suffix)
        
        output_path.write_text(header + content, encoding='utf-8')
        return output_path

    async def _convert_binary(self, input_path: Path, output_path: Path, suffix: str) -> Path:
        """Optimized binary handler: Provides both Base64 and a Hex-Dump for analysis."""
        with open(input_path, 'rb') as f:
            binary_data = f.read()
            
        # Base64 encoding
        encoded = base64.b64encode(binary_data).decode('utf-8')
        
        # Hex dump for the first 256 bytes (Professional touch)
        hex_dump = binascii.hexlify(binary_data[:256], ' ').decode('utf-8')
        
        header = (
            f"--- DETECTED BINARY FORMAT ({suffix}) ---\n"
            f"Size: {len(binary_data)} bytes\n"
            f"Hex Header (First 256b):\n{hex_dump}\n"
            f"--------------------------------------------------\n"
            f"FULL BASE64 STREAM:\n"
        )
        
        output_path.write_text(header + encoded, encoding='utf-8')
        return output_path

# Register as the global fallback
registry.set_fallback(UniversalFallbackConverter())
