import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import List, Optional
import uuid
import json
import asyncio
import redis.asyncio as redis

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from celery.result import AsyncResult

from app.core.graph import engine
from app.core.registry_instance import registry
from app.worker import celery_app, conversion_task
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
    target_format: str = Form(...),
    options: str = Form(None)
):
    """Triggers an asynchronous conversion task and logs it to history."""
    import json
    filename = file.filename or "uploaded_file"
    task_id = str(uuid.uuid4())
    
    # Parse options
    parsed_options = None
    if options:
        try:
            parsed_options = json.loads(options)
        except:
            parsed_options = {}
    
    # Create storage directories
    uploads_dir = Path(tempfile.gettempdir()) / "proton_uploads"
    downloads_dir = Path(tempfile.gettempdir()) / "proton_downloads"
    uploads_dir.mkdir(exist_ok=True)
    downloads_dir.mkdir(exist_ok=True)
    
    input_path = uploads_dir / f"{task_id}_{filename}"
    final_filename = f"converted_{task_id}_{Path(filename).stem}.{target_format}"
    output_path = downloads_dir / final_filename
    
    try:
        # Save uploaded file
        with input_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Trigger Celery task
        conversion_task.delay(str(input_path), target_format, str(output_path), parsed_options)
        
        # Log to History in Redis
        redis_client = celery_app.backend
        history_entry = {
            "task_id": task_id,
            "filename": filename,
            "target": target_format,
            "timestamp": time.time(),
            "status": "pending"
        }
        # Store as a list of JSON strings
        redis_client.lpush("proton_history", json.dumps(history_entry))
        # Keep only last 20
        redis_client.ltrim("proton_history", 0, 19)
        
        return {"task_id": task_id, "status": "pending"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting conversion: {str(e)}")

@app.get("/history")
async def get_history():
    """Returns the last 20 conversion requests."""
    redis_client = celery_app.backend
    history_raw = redis_client.lrange("proton_history", 0, -1)
    
    history = []
    for item in history_raw:
        data = json.loads(item)
        # Update status from Celery result
        res = AsyncResult(data["task_id"], app=celery_app)
        data["status"] = res.state if res.state != 'PENDING' else 'processing'
        history.append(data)
        
    return {"history": history}

@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Checks the status of a conversion task."""
    result = AsyncResult(task_id, app=celery_app)
    
    if result.state == 'PENDING':
        return {"status": "pending"}
    elif result.state == 'SUCCESS':
        return {"status": "completed", "result": result.result}
    elif result.state == 'FAILURE':
        return {"status": "failed", "error": str(result.info)}
    else:
        return {"status": result.state}

@app.get("/download/{task_id}")
async def download_result(task_id: str):
    """Downloads the result of a completed conversion task."""
    result = AsyncResult(task_id, app=celery_app)
    
    if result.state != 'SUCCESS':
        raise HTTPException(status_code=400, detail="Conversion not completed yet or failed.")
    
    output_path = Path(result.result.get("output_path"))
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Converted file not found on disk.")
        
    return FileResponse(
        path=output_path,
        filename=output_path.name,
        media_type="application/octet-stream"
    )

@app.post("/convert-batch")
async def convert_batch(
    files: List[UploadFile] = File(...),
    target_format: str = Form(...),
    options: str = Form(None)
):
    """Triggers batch conversion of multiple files."""
    batch_id = str(uuid.uuid4())
    parsed_options = json.loads(options) if options else {}
    
    uploads_dir = Path(tempfile.gettempdir()) / "proton_uploads"
    downloads_dir = Path(tempfile.gettempdir()) / "proton_downloads"
    uploads_dir.mkdir(exist_ok=True)
    downloads_dir.mkdir(exist_ok=True)
    
    task_ids = []
    for file in files:
        filename = file.filename or "uploaded_file"
        task_id = str(uuid.uuid4())
        
        input_path = uploads_dir / f"{task_id}_{filename}"
        final_filename = f"batch_{batch_id}_{task_id}_{Path(filename).stem}.{target_format}"
        output_path = downloads_dir / final_filename
        
        with input_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        conversion_task.delay(str(input_path), target_format, str(output_path), parsed_options)
        task_ids.append(task_id)
    
    # Store batch mapping in Redis
    redis_client = celery_app.backend
    redis_client.set(f"batch:{batch_id}", json.dumps(task_ids))
    
    return {"batch_id": batch_id, "task_count": len(task_ids)}

@app.get("/batch-status/{batch_id}")
async def get_batch_status(batch_id: str):
    """Checks the overall status of a batch conversion."""
    redis_client = celery_app.backend
    task_ids_raw = redis_client.get(f"batch:{batch_id}")
    if not task_ids_raw:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    task_ids = json.loads(task_ids_raw)
    results = []
    completed_count = 0
    
    for tid in task_ids:
        res = AsyncResult(tid, app=celery_app)
        results.append({"task_id": tid, "status": res.state})
        if res.state == 'SUCCESS':
            completed_count += 1
            
    return {
        "batch_id": batch_id,
        "total": len(task_ids),
        "completed": completed_count,
        "progress": (completed_count / len(task_ids)) * 100,
        "tasks": results
    }

@app.post("/tool/execute")
async def execute_tool(
    tool_id: str = Form(...),
    files: List[UploadFile] = File(...),
    options: str = Form(None)
):
    """Executes a specialized tool (PDF Merge, Audio Trim, etc.)"""
    import json
    parsed_options = json.loads(options) if options else {}
    
    uploads_dir = Path(tempfile.gettempdir()) / "proton_uploads"
    downloads_dir = Path(tempfile.gettempdir()) / "proton_downloads"
    uploads_dir.mkdir(exist_ok=True)
    downloads_dir.mkdir(exist_ok=True)
    
    task_id = str(uuid.uuid4())
    
    # Save all files
    saved_files = []
    for file in files:
        path = uploads_dir / f"{task_id}_{file.filename}"
        with path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(str(path))
    
    # Use the first file as primary input for the engine
    primary_input = Path(saved_files[0])
    # Tool outputs usually maintain the same extension as input
    output_path = downloads_dir / f"tool_{task_id}_{primary_input.name}"
    
    # Inject saved files into options for tools that need multiple files (merge)
    parsed_options["files"] = saved_files
    
    # We use a dummy 'target_format' as tool converters often maintain format
    target_format = primary_input.suffix[1:].lower()
    
    # Trigger Celery task (reusing conversion_task)
    conversion_task.delay(str(primary_input), target_format, str(output_path), parsed_options, tool_id=tool_id)
    
    return {"task_id": task_id, "status": "pending"}

@app.websocket("/ws/status/{task_id}")
async def websocket_status(websocket: WebSocket, task_id: str):
    """Real-time progress updates for a conversion task."""
    await websocket.accept()
    
    # Connect to Redis Pub/Sub
    r = redis.from_url(celery_app.conf.broker_url)
    pubsub = r.pubsub()
    await pubsub.subscribe(f"task_progress_{task_id}")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"].decode("utf-8")
                await websocket.send_text(data)
                
                # If completed or failed, close the socket
                progress_data = json.loads(data)
                if progress_data["status"] in ["completed", "failed"]:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"task_progress_{task_id}")
        await r.close()


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
    port = int(os.getenv("PORT", 1776))
    # Explicitly set workers to 1 for Render Free Tier to avoid memory issues
    uvicorn.run(app, host="0.0.0.0", port=port, workers=1, timeout_keep_alive=5)
