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

    async def convert(self, input_path: Path, output_path: Path, options: dict = None) -> Path:
        with Image.open(input_path) as img:
            # Handle Resizing
            if options:
                width = options.get("width")
                height = options.get("height")
                if width or height:
                    orig_w, orig_h = img.size
                    if width and not height:
                        height = int(orig_h * (width / orig_w))
                    elif height and not width:
                        width = int(orig_w * (height / orig_h))
                    img = img.resize((width, height), Image.Resampling.LANCZOS)

            fmt = self._target_fmt.lower()
            pillow_format = {"jpg": "JPEG", "jpeg": "JPEG", "jfif": "JPEG"}.get(fmt, fmt.upper())
            if fmt in ("jpg", "jpeg", "jfif"):
                img = img.convert("RGB")
            
            save_args = {"format": pillow_format}
            if options and "quality" in options:
                save_args["quality"] = options["quality"]
            
            img.save(output_path, **save_args)
        return output_path

# Expanded list of image formats supported by Pillow
image_extensions = [
    "png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "tif", "ico", 
    "eps", "pdf", "pxm", "tga", "heif", "heic", "avif", "cur", "pcx", "jfif"
]
registry.register_family("image", image_extensions)

for fmt in image_extensions:
    registry.register(ImageFamilyConverter(fmt))
