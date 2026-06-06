import asyncio
import httpx
import os
from pathlib import Path
from PIL import Image

async def test_full_pipeline():
    base_url = "http://localhost:8000"
    test_dir = Path("pipeline_tests")
    test_dir.mkdir(exist_ok=True)
    
    print("Starting Full-Stack Pipeline Tests...")
    
    # 1. Create test files
    # Image
    img = Image.new('RGB', (64, 64), color='red')
    img_path = test_dir / "test.png"
    img.save(img_path)
    
    # PDF (via Pillow)
    pdf_path = test_dir / "test.pdf"
    img.save(pdf_path, "PDF")
    
    # JSON
    json_path = test_dir / "test.json"
    json_path.write_text('{"name": "Proton", "version": "2.0"}', encoding='utf-8')
    
    # MP4 (via FFmpeg)
    import subprocess
    mp4_path = test_dir / "test.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=64x64:rate=1", str(mp4_path)], capture_output=True)

    test_cases = [
        ("test.png", "jpg", "Image -> Image"),
        ("test.pdf", "png", "PDF -> Image"),
        ("test.png", "pdf", "Image -> PDF"),
        ("test.mp4", "png", "Media -> Image"),
        ("test.png", "mp4", "Image -> Media"),
        ("test.json", "csv", "Data -> Data"),
        ("test.json", "txt", "Data -> Doc"),
        ("test.pdf", "mp4", "PDF -> Media (Multi-hop)"),
    ]

    passed = 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        for filename, target, desc in test_cases:
            print(f"Testing {desc}: {filename} -> {target}...", end=" ")
            file_path = test_dir / filename
            
            try:
                with open(file_path, "rb") as f:
                    files = {"file": (filename, f, "application/octet-stream")}
                    data = {"target_format": target}
                    res = await client.post(f"{base_url}/convert", files=files, data=data)
                
                if res.status_code == 200:
                    print("PASSED")
                    passed += 1
                else:
                    print(f"FAILED (HTTP {res.status_code})")
            except Exception as e:
                print(f"ERROR ({type(e).__name__})")

    print(f"Final Score: {passed}/{len(test_cases)} pipelines functional.")

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
