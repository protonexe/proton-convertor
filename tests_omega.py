import asyncio
import os
import shutil
from pathlib import Path
from PIL import Image
import subprocess
from app.core.graph import engine
from app.core.registry_instance import registry

async def run_comprehensive_test():
    print("Starting Omega-Level Permutation Test Suite...")
    
    all_formats = registry.get_all_formats()
    print(f"Detected {len(all_formats)} supported formats: {all_formats}")
    
    test_dir = Path("stress_tests")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir()

    print("\nGenerating sample files...")
    for fmt in all_formats:
        path = test_dir / f"sample.{fmt}"
        try:
            if fmt in ["png", "jpg", "jpeg", "webp", "bmp", "gif", "ico"]:
                img = Image.new('RGB', (32, 32), color='blue')
                img.save(path)
            elif fmt == "pdf":
                img = Image.new('RGB', (32, 32), color='blue')
                img.save(path, "PDF")
            elif fmt in ["json", "csv", "yaml", "yml", "xml", "xlsx", "xls"]:
                path.write_text('{"test": "data"}', encoding='utf-8')
            elif fmt in ["mp4", "avi", "mkv", "mov"]:
                subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=32x32:rate=1", str(path)], capture_output=True)
            elif fmt in ["mp3", "wav", "ogg"]:
                subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=1000:duration=1", str(path)], capture_output=True)
            else:
                path.write_text("Universal fallback content", encoding='utf-8')
        except Exception as e:
            print(f"Warning: Could not create sample for {fmt}: {e}")

    print("\nTesting all permutations...")
    total_tests = len(all_formats) * len(all_formats)
    passed = 0
    failed = 0
    errors = []

    for src in all_formats:
        for target in all_formats:
            if src == target:
                passed += 1
                continue
                
            try:
                path = engine.find_path(src, target)
                if path is None:
                    failed += 1
                    errors.append(f"No path: {src} -> {target}")
                    continue
                
                input_path = test_dir / f"sample.{src}"
                if not input_path.exists():
                    input_path.write_text("fallback", encoding='utf-8')
                
                output_path = test_dir / f"out_{src}_to_{target}.{target}"
                await engine.convert(input_path, output_path)
                
                if output_path.exists():
                    passed += 1
                else:
                    failed += 1
                    errors.append(f"File not created: {src} -> {target}")
                    
            except Exception as e:
                failed += 1
                errors.append(f"Crash {src} -> {target}: {type(e).__name__}")

    print(f"\n--- FINAL RESULTS ---")
    print(f"Total Combinations: {total_tests}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if errors:
        print("\nTop Failures:")
        for err in errors[:20]:
            print(err)

if __name__ == "__main__":
    asyncio.run(run_comprehensive_test())
