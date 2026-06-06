import os
import shutil
import tempfile
from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.core.graph import engine
from app.core.registry_instance import registry
import app.converters # Ensure converters are registered

app = FastAPI(title="Proton Convertor")

# Models for API responses
class PathStep(BaseModel):
    source: str
    target: str

class PathResponse(BaseModel):
    path: List[PathStep]
    total_steps: int

@app.get("/formats")
async def get_formats():
    """Returns a list of all supported file formats."""
    return {"formats": registry.get_all_formats()}

@app.get("/path")
async def get_conversion_path(src: str, target: str):
    """Finds the conversion path between two formats."""
    path = engine.find_path(src, target)
    if path is None:
        raise HTTPException(status_code=404, detail=f"No conversion path from {src} to {target}")
    
    steps = [PathStep(source=c.source_format, target=c.target_format) for c in path]
    return PathResponse(path=steps, total_steps=len(steps))

@app.post("/convert")
async def convert_file(
    file: UploadFile = File(...),
    target_format: str = Form(...)
):
    """Uploads a file and converts it to the target format."""
    filename = file.filename or "uploaded_file"
    
    # Create a persistent temp directory for the session
    # Using /tmp on Linux (Render) is faster and safer
    session_dir = Path(tempfile.gettempdir()) / f"proton_{os.getpid()}"
    session_dir.mkdir(exist_ok=True)
    
    input_path = session_dir / filename
    
    try:
        # Save uploaded file
        with input_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Perform conversion
        result_path = await engine.convert(input_path, target_format)
        
        # Prepare final output path
        downloads_dir = Path(tempfile.gettempdir()) / "proton_downloads"
        downloads_dir.mkdir(exist_ok=True)
        
        final_filename = f"converted_{Path(filename).stem}.{target_format}"
        final_path = downloads_dir / final_filename
        shutil.copy2(result_path, final_path)
        
        return FileResponse(
            path=final_path, 
            filename=f"{Path(filename).stem}.{target_format}",
            media_type="application/octet-stream"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the error for the server admin
        print(f"CRITICAL CONVERSION ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")
    finally:
        # Cleanup session files but keep the final result for the response
        try:
            if input_path.exists():
                input_path.unlink()
        except:
            pass


# Serve frontend
# We'll put the frontend in app/templates/index.html
# Since it's a single page, we can just serve it.
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("app/templates/index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    # Explicitly set workers to 1 for Render Free Tier to avoid memory issues
    uvicorn.run(app, host="0.0.0.0", port=port, workers=1, timeout_keep_alive=5)
