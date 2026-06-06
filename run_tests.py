import asyncio
import os
import shutil
from pathlib import Path
from app.core.graph import engine
from app.core.registry_instance import registry

async def test_conversion(src_path: Path, target_fmt: str, name: str):
    print(f"Testing {name}: {src_path.name} -> {target_fmt}...", end=" ")
    try:
        result = await engine.convert(src_path, target_fmt)
        if result.exists():
            print("✅ SUCCESS")
            result.unlink()
        else:
            print("❌ FAILED (Result file not found)")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

async def main():
    # Setup test files
    test_dir = Path("test_files")
    test_dir.mkdir(exist_ok=True)
    
    # 1. Test Image (PIL)
    from PIL import Image
    img_path = test_dir / "test.png"
    Image.new('RGB', (100, 100), color='red').save(img_path)
    
    # 2. Test OCR (Tesseract) - Create a simple image with text
    # Since we can't easily create an image with text without more libs, 
    # we'll just check if the converter is registered and try to run it on a blank image.
    
    # 3. Test Vector (SVG)
    svg_path = test_dir / "test.svg"
    svg_path.write_text('<svg height="100" width="100"><circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" /></svg>')

    # 4. Test Ebook (EPUB) - This is harder to mock, we'll just verify registration
    
    print("--- Starting Conversion Tests ---")
    await test_conversion(img_path, "jpg", "Image Converter")
    await test_conversion(img_path, "pdf", "Image to PDF")
    await test_conversion(svg_path, "png", "SVG to PNG")
    await test_conversion(svg_path, "pdf", "SVG to PDF")
    await test_conversion(img_path, "txt", "OCR Converter")
    
    # Cleanup
    shutil.rmtree(test_dir)
    print("--- Tests Completed ---")

if __name__ == "__main__":
    asyncio.run(main())
