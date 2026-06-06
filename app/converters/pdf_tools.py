from pathlib import Path
from typing import List
from pypdf import PdfReader, PdfWriter
from app.converters.base import BaseConverter
from app.core.registry_instance import registry

class PdfToolConverter(BaseConverter):
    def __init__(self, action: str):
        self._action = action

    @property
    def source_format(self) -> str: return "pdf"
    @property
    def target_format(self) -> str: return "pdf"

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
        # Note: This is used for tools like merge/split. 
        # In a real system, input_path might be a directory or a list of files.
        # For the base interface, we'll handle specific actions.
        
        if self._action == "merge":
            # Expects options['files'] to be a list of paths
            files = options.get("files", [str(input_path)])
            merger = PdfWriter()
            for pdf in files:
                merger.append(pdf)
            merger.write(str(output_path))
            merger.close()
            
        elif self._action == "split":
            # Expects options['page_range'] (e.g., "1-3")
            reader = PdfReader(str(input_path))
            writer = PdfWriter()
            start, end = map(int, options.get("page_range", "1-1").split("-"))
            for i in range(start-1, min(end, len(reader.pages))):
                writer.add_page(reader.pages[i])
            with open(output_path, "wb") as f:
                writer.write(f)
        
        elif self._action == "rotate":
            # Expects options['degrees'] (e.g., 90)
            reader = PdfReader(str(input_path))
            writer = PdfWriter()
            degrees = options.get("degrees", 90)
            for page in reader.pages:
                page.rotate(degrees)
                writer.add_page(page)
            with open(output_path, "wb") as f:
                writer.write(f)
        
        return output_path

# Register tools as specialized converters
registry.register(PdfToolConverter("merge"))
registry.register(PdfToolConverter("split"))
registry.register(PdfToolConverter("rotate"))
