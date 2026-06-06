import asyncio
import os
from pathlib import Path
from PIL import Image
from app.core.graph import engine
from app.core.registry_instance import registry

async def run_tests():
    print("Starting Proton Convertor Validation Suite...")
    
    # Test cases: (source_ext, target_ext, description)
    test_cases = [
        ("png", "jpg", "Image to Image"),
        ("pdf", "png", "PDF to Image"),
        ("png", "pdf", "Image to PDF"),
        ("mp4", "png", "Media to Image"),
        ("png", "mp4", "Image to Media"),
        ("json", "csv", "Data to Data"),
        ("csv", "txt", "Data to Doc"),
        ("txt", "pdf", "Doc to Doc"),
        ("xyz", "png", "Esoteric to Image (Universal Fallback)"),
        ("pdf", "mp4", "PDF to Media (Multi-hop)"),
    ]
    
    test_dir = Path("tests_temp")
    test_dir.mkdir(exist_ok=True)
    
    # CREATE REAL VALID MINIMAL FILES
    # 64x64 PNG (FFmpeg requires even dimensions for yuv420p)
    img = Image.new('RGB', (64, 64), color='red')
    img.save(test_dir / "test.png")
    
    # Dummy JSON
    (test_dir / "test.json").write_text('{"key": "value"}', encoding='utf-8')
    
    # Dummy CSV
    (test_dir / "test.csv").write_text('key,value\\n1,test', encoding='utf-8')
    
    # Dummy TXT
    (test_dir / "test.txt").write_text('Proton Test Content', encoding='utf-8')
    
    # Dummy XYZ (Esoteric)
    (test_dir / "test.xyz").write_text('Some weird binary data', encoding='utf-8')
    
    # Dummy MP4 (We create a tiny valid one using ffmpeg)
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=64x64:rate=1", str(test_dir / "test.mp4")], capture_output=True)
    
    # Dummy PDF (A simple one using Pillow)
    img.save(test_dir / "test.pdf", "PDF")

    passed = 0
    for src, target, desc in test_cases:
        print(f"Testing {desc}: {src} -> {target}...", end=" ")
        try:
            path = engine.find_path(src, target)
            if path is None:
                print("FAILED (No Path)")
                continue
            
            input_path = test_dir / f"test.{src}"
            if not input_path.exists():
                input_path.write_text("fallback content", encoding='utf-8')
                
            await engine.convert(input_path, target)
            print("PASSED")
            passed += 1
        except Exception as e:
            print(f"ERROR ({type(e).__name__})")
            
    print(f"Summary: {passed}/{len(test_cases)} conversions passed.")

if __name__ == "__main__":
    asyncio.run(run_tests())
