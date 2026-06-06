import ebooklib
from ebooklib import epub
from pathlib import Path
from app.converters.base import BaseConverter
from app.core.registry_instance import registry
import html2text

class EbookConverter(BaseConverter):
    def __init__(self, src: str, target: str):
        self._src = src
        self._target = target

    @property
    def source_format(self) -> str: return self._src
    @property
    def target_format(self) -> str: return self._target

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
        book = epub.read_epub(str(input_path))
        content = []
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                content.append(html2text.html2text(item.get_content().decode('utf-8')))
        
        full_text = "\\n".join(content)
        
        if self._target == "txt":
            output_path.write_text(full_text, encoding='utf-8')
        elif self._target == "md":
            output_path.write_text(f"# {book.get_metadata('DC', 'title')[0][0]}\n\n{full_text}", encoding='utf-8')
        else:
            output_path.write_text(full_text, encoding='utf-8')
            
        return output_path

# Register EPUB -> TXT, MD
registry.register(EbookConverter("epub", "txt"))
registry.register(EbookConverter("epub", "md"))
