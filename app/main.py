import os
import shutil
import tempfile
import time
import uuid
import json
import asyncio
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel

from app.core.graph import engine
from app.core.registry_instance import registry
import app.converters  # Ensure converters are registered

app = FastAPI(title="Proton Convertor")

# In-memory task store (no Redis required)
tasks_store: Dict[str, Dict[str, Any]] = {}
tasks_lock = threading.Lock()

uploads_dir = Path(tempfile.gettempdir()) / "proton_uploads"
downloads_dir = Path(tempfile.gettempdir()) / "proton_downloads"
uploads_dir.mkdir(exist_ok=True)
downloads_dir.mkdir(exist_ok=True)


class PathStep(BaseModel):
    source: str
    target: str


class PathResponse(BaseModel):
    path: List[PathStep]
    total_steps: int


@app.get("/formats")
async def get_formats():
    return {"formats": registry.get_all_formats()}


@app.get("/path")
async def get_conversion_path(src: str, target: str):
    path = engine.find_path(src, target)
    if path is None:
        raise HTTPException(status_code=404, detail=f"No conversion path from {src} to {target}")

    steps = [PathStep(source=c.source_format, target=c.target_format) for c in path]
    return PathResponse(path=steps, total_steps=len(steps))


def _run_conversion(task_id: str, input_path: Path, target_format: str, output_path: Path, options: dict = None, tool_id: str = None):
    """Background worker that runs the conversion."""
    with tasks_lock:
        tasks_store[task_id]["status"] = "processing"
        tasks_store[task_id]["progress"] = 10

    try:
        if tool_id:
            from app.core.registry_instance import registry as reg
            tool = reg.get_tool(tool_id)
            if not tool:
                raise ValueError(f"Tool {tool_id} not found in registry")
            result_path = asyncio.run(tool.convert(input_path, output_path, options=options))
        else:
            result_path = asyncio.run(engine.convert(input_path, target_format, options=options))

        with tasks_lock:
            tasks_store[task_id]["progress"] = 90

        if result_path.exists() and result_path != output_path:
            shutil.move(str(result_path), str(output_path))

        with tasks_lock:
            tasks_store[task_id]["status"] = "completed"
            tasks_store[task_id]["progress"] = 100
            tasks_store[task_id]["output_path"] = str(output_path)

    except Exception as e:
        import traceback
        traceback.print_exc()
        with tasks_lock:
            tasks_store[task_id]["status"] = "failed"
            tasks_store[task_id]["error"] = str(e)


@app.post("/convert")
async def convert_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_format: str = Form(...),
    options: str = Form(None)
):
    filename = file.filename or "uploaded_file"
    task_id = str(uuid.uuid4())

    parsed_options = None
    if options:
        try:
            parsed_options = json.loads(options)
        except Exception:
            parsed_options = {}

    input_path = uploads_dir / f"{task_id}_{filename}"
    final_filename = f"converted_{task_id}_{Path(filename).stem}.{target_format}"
    output_path = downloads_dir / final_filename

    try:
        with input_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        with tasks_lock:
            tasks_store[task_id] = {
                "task_id": task_id,
                "filename": filename,
                "target": target_format,
                "timestamp": time.time(),
                "status": "pending",
                "progress": 0,
                "output_path": None,
                "error": None,
            }

        background_tasks.add_task(_run_conversion, task_id, input_path, target_format, output_path, parsed_options)

        return {"task_id": task_id, "status": "pending"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting conversion: {str(e)}")


@app.get("/history")
async def get_history():
    with tasks_lock:
        history = []
        for item in sorted(tasks_store.values(), key=lambda x: x["timestamp"], reverse=True)[:20]:
            history.append({
                "task_id": item["task_id"],
                "filename": item["filename"],
                "target": item["target"],
                "timestamp": item["timestamp"],
                "status": item["status"],
            })
    return {"history": history}


@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    with tasks_lock:
        task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": task["status"], "progress": task.get("progress", 0)}


@app.get("/download/{task_id}")
async def download_result(task_id: str):
    with tasks_lock:
        task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Conversion not completed yet or failed.")

    output_path = Path(task["output_path"])
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Converted file not found on disk.")

    return FileResponse(
        path=output_path,
        filename=output_path.name,
        media_type="application/octet-stream"
    )


@app.post("/convert-batch")
async def convert_batch(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    target_format: str = Form(...),
    options: str = Form(None)
):
    batch_id = str(uuid.uuid4())
    parsed_options = json.loads(options) if options else {}

    task_ids = []
    for file in files:
        filename = file.filename or "uploaded_file"
        task_id = str(uuid.uuid4())

        input_path = uploads_dir / f"{task_id}_{filename}"
        final_filename = f"batch_{batch_id}_{task_id}_{Path(filename).stem}.{target_format}"
        output_path = downloads_dir / final_filename

        with input_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        with tasks_lock:
            tasks_store[task_id] = {
                "task_id": task_id,
                "filename": filename,
                "target": target_format,
                "timestamp": time.time(),
                "status": "pending",
                "progress": 0,
                "output_path": None,
                "error": None,
                "batch_id": batch_id,
            }

        background_tasks.add_task(_run_conversion, task_id, input_path, target_format, output_path, parsed_options)
        task_ids.append(task_id)

    return {"batch_id": batch_id, "task_count": len(task_ids)}


@app.get("/batch-status/{batch_id}")
async def get_batch_status(batch_id: str):
    with tasks_lock:
        batch_tasks = [t for t in tasks_store.values() if t.get("batch_id") == batch_id]

    if not batch_tasks:
        raise HTTPException(status_code=404, detail="Batch not found")

    completed_count = sum(1 for t in batch_tasks if t["status"] == "completed")
    return {
        "batch_id": batch_id,
        "total": len(batch_tasks),
        "completed": completed_count,
        "progress": (completed_count / len(batch_tasks)) * 100 if batch_tasks else 0,
        "tasks": [{"task_id": t["task_id"], "status": t["status"]} for t in batch_tasks]
    }


@app.post("/tool/execute")
async def execute_tool(
    background_tasks: BackgroundTasks,
    tool_id: str = Form(...),
    files: List[UploadFile] = File(...),
    options: str = Form(None)
):
    parsed_options = {}
    if options:
        try:
            parsed_options = json.loads(options)
        except Exception:
            parsed_options = {}

    task_id = str(uuid.uuid4())

    saved_files = []
    for file in files:
        path = uploads_dir / f"{task_id}_{file.filename}"
        with path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(str(path))

    primary_input = Path(saved_files[0])
    output_path = downloads_dir / f"tool_{task_id}_{primary_input.name}"

    parsed_options["files"] = saved_files

    target_format = primary_input.suffix[1:].lower()

    with tasks_lock:
        tasks_store[task_id] = {
            "task_id": task_id,
            "filename": primary_input.name,
            "target": target_format,
            "timestamp": time.time(),
            "status": "pending",
            "progress": 0,
            "output_path": None,
            "error": None,
        }

    background_tasks.add_task(_run_conversion, task_id, primary_input, target_format, output_path, parsed_options, tool_id=tool_id)

    return {"task_id": task_id, "status": "pending"}


@app.websocket("/ws/status/{task_id}")
async def websocket_status(websocket: WebSocket, task_id: str):
    await websocket.accept()

    try:
        while True:
            with tasks_lock:
                task = tasks_store.get(task_id)

            if not task:
                await websocket.send_text(json.dumps({"status": "failed", "progress": 0, "error": "Task not found"}))
                break

            await websocket.send_text(json.dumps({
                "status": task["status"],
                "progress": task.get("progress", 0)
            }))

            if task["status"] in ["completed", "failed"]:
                break

            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        pass


@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("app/templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, workers=1, timeout_keep_alive=5)
