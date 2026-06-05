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
    # Create temporary directory for this specific conversion request
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        filename = file.filename or "uploaded_file"
        input_path = tmp_path / filename
        
        # Save uploaded file
        with input_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            # Perform conversion using the graph engine
            result_path = await engine.convert(input_path, target_format)
            
            # Use the safe filename for the resulting file
            downloads_dir = Path("downloads")
            downloads_dir.mkdir(exist_ok=True)
            
            safe_filename = filename
            final_filename = f"converted_{Path(safe_filename).stem}.{target_format}"
            final_path = downloads_dir / final_filename
            shutil.copy2(result_path, final_path)
            
            return FileResponse(
                path=final_path, 
                filename=f"{Path(safe_filename).stem}.{target_format}",
                media_type="application/octet-stream"
            )
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")


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
    uvicorn.run(app, host="0.0.0.0", port=port)
