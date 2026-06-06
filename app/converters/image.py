from pathlib import Path
from PIL import Image
from app.converters.base import BaseConverter
from app.core.registry_instance import registry

class ImageFamilyConverter(BaseConverter):
    def __init__(self, target_fmt: str):
        self._target_fmt = target_fmt

    @property
    def source_format(self) -> str:
        return "image" # Registered as family

    @property
    def target_format(self) -> str:
        return self._target_fmt

    async def convert(self, input_path: Path, output_path: Path) -> Path:
        with Image.open(input_path) as img:
            if self._target_fmt.lower() in ["jpg", "jpeg"]:
                img = img.convert("RGB")
            img.save(output_path, format=self._target_fmt.upper() if self._target_fmt.lower() != "jpg" else "JPEG")
        return output_path

# Expanded list of image formats supported by Pillow
image_extensions = [
    "png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif", "ico", 
    "eps", "pdf", "pxm", "tga", "heif", "heic", "avif", "cur", "pcx", "jfif"
]
registry.register_family("image", image_extensions)

for fmt in image_extensions:
    registry.register(ImageFamilyConverter(fmt))
