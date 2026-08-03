import os
import shutil
import tempfile
import time
import uuid
import json
import asyncio
import threading
import re
import subprocess
import zipfile
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel

from app.core.graph import engine
from app.core.registry_instance import registry
from app.core.mime import detect_format
import app.converters

app = FastAPI(title="Proton Convertor")

# In-memory stores
tasks_store: Dict[str, Dict[str, Any]] = {}
tasks_lock = threading.Lock()
history_store: List[Dict[str, Any]] = []
MAX_HISTORY = 50

uploads_dir = Path(tempfile.gettempdir()) / "proton_uploads"
downloads_dir = Path(tempfile.gettempdir()) / "proton_downloads"
uploads_dir.mkdir(exist_ok=True)
downloads_dir.mkdir(exist_ok=True)

# Format categories for the UI
FORMAT_CATEGORIES = {
    "image": {
        "label": "Image",
        "icon": "fa-image",
        "color": "blue",
        "formats": ["jpg", "jpeg", "png", "webp", "bmp", "gif", "tiff", "tif", "ico", "jfif", "heif", "heic", "avif", "pdf"]
    },
    "video": {
        "label": "Video",
        "icon": "fa-video",
        "color": "purple",
        "formats": ["mp4", "avi", "mkv", "mov", "wmv", "flv", "webm", "m4v", "3gp", "ts", "gif"]
    },
    "audio": {
        "label": "Audio",
        "icon": "fa-music",
        "color": "green",
        "formats": ["mp3", "wav", "ogg", "m4a", "flac", "aac", "opus", "wma"]
    },
    "document": {
        "label": "Document",
        "icon": "fa-file-lines",
        "color": "red",
        "formats": ["pdf", "txt", "md", "html", "docx", "epub"]
    },
    "data": {
        "label": "Data",
        "icon": "fa-database",
        "color": "amber",
        "formats": ["json", "csv", "yaml", "yml", "xml", "xlsx", "xls"]
    }
}

# Device presets
DEVICE_PRESETS = {
    "iphone": {"label": "iPhone", "icon": "fa-mobile-screen", "configs": {
        "video": {"format": "mp4", "options": {"bitrate": "5M"}},
        "audio": {"format": "m4a", "options": {"bitrate": "128k"}},
        "image": {"format": "heic", "options": {"width": 1170, "quality": 85}},
    }},
    "android": {"label": "Android", "icon": "fa-mobile-screen-button", "configs": {
        "video": {"format": "mp4", "options": {"bitrate": "4M"}},
        "audio": {"format": "ogg", "options": {"bitrate": "128k"}},
        "image": {"format": "webp", "options": {"width": 1080, "quality": 80}},
    }},
    "web": {"label": "Web Optimized", "icon": "fa-globe", "configs": {
        "video": {"format": "webm", "options": {"bitrate": "2M"}},
        "audio": {"format": "ogg", "options": {"bitrate": "128k"}},
        "image": {"format": "webp", "options": {"width": 1200, "quality": 80}},
    }},
    "discord": {"label": "Discord", "icon": "fa-comment", "configs": {
        "video": {"format": "mp4", "options": {"bitrate": "8M"}},
        "audio": {"format": "ogg", "options": {"bitrate": "128k"}},
        "image": {"format": "png", "options": {}},
    }},
}


class PathStep(BaseModel):
    source: str
    target: str


class PathResponse(BaseModel):
    path: List[PathStep]
    total_steps: int


def _format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _add_history(task_id: str, filename: str, target: str, status: str, input_size: int = 0):
    entry = {
        "task_id": task_id,
        "filename": filename,
        "target": target,
        "timestamp": time.time(),
        "status": status,
        "input_size": input_size,
        "input_size_fmt": _format_size(input_size) if input_size else "",
    }
    with tasks_lock:
        history_store.insert(0, entry)
        if len(history_store) > MAX_HISTORY:
            history_store.pop()


def _update_history_status(task_id: str, status: str, output_path: str = None, output_size: int = 0):
    with tasks_lock:
        for entry in history_store:
            if entry["task_id"] == task_id:
                entry["status"] = status
                if output_path:
                    entry["output_path"] = output_path
                    entry["output_size"] = output_size
                    entry["output_size_fmt"] = _format_size(output_size)
                break


def _get_compatible_formats(source_ext: str) -> Dict[str, List[str]]:
    """Returns compatible target formats grouped by category."""
    result = {}
    source_ext = source_ext.lower()
    for cat_key, cat in FORMAT_CATEGORIES.items():
        compatible = []
        for fmt in cat["formats"]:
            if fmt != source_ext:
                path = engine.find_path(source_ext, fmt)
                if path is not None:
                    compatible.append(fmt)
        if compatible:
            result[cat_key] = {
                "label": cat["label"],
                "icon": cat["icon"],
                "color": cat["color"],
                "formats": sorted(compatible)
            }
    return result


def _run_conversion(task_id: str, input_path: Path, target_format: str, output_path: Path, options: dict = None, tool_id: str = None):
    """Background worker that runs the conversion with progress tracking."""
    with tasks_lock:
        tasks_store[task_id]["status"] = "converting"
        tasks_store[task_id]["progress"] = 5
        tasks_store[task_id]["phase"] = "Preparing"

    try:
        if tool_id:
            from app.core.registry_instance import registry as reg
            tool = reg.get_tool(tool_id)
            if not tool:
                raise ValueError(f"Tool {tool_id} not found")
            with tasks_lock:
                tasks_store[task_id]["phase"] = "Processing"
                tasks_store[task_id]["progress"] = 20
            result_path = asyncio.run(tool.convert(input_path, output_path, options=options))
        else:
            with tasks_lock:
                tasks_store[task_id]["phase"] = "Analyzing"
                tasks_store[task_id]["progress"] = 10

            path = engine.find_path(
                detect_format(input_path) or input_path.suffix[1:].lower(),
                target_format
            )
            if not path:
                raise ValueError(f"No conversion path found")

            with tasks_lock:
                tasks_store[task_id]["phase"] = "Converting"
                tasks_store[task_id]["progress"] = 20

            result_path = asyncio.run(engine.convert(input_path, target_format, options=options))

        with tasks_lock:
            tasks_store[task_id]["progress"] = 90
            tasks_store[task_id]["phase"] = "Finalizing"

        if result_path.exists() and result_path != output_path:
            shutil.move(str(result_path), str(output_path))

        if not output_path.exists():
            raise ValueError("Conversion produced no output file")

        output_size = output_path.stat().st_size

        with tasks_lock:
            tasks_store[task_id]["status"] = "completed"
            tasks_store[task_id]["progress"] = 100
            tasks_store[task_id]["phase"] = "Done"
            tasks_store[task_id]["output_path"] = str(output_path)
            tasks_store[task_id]["output_size"] = output_size
            tasks_store[task_id]["output_size_fmt"] = _format_size(output_size)

        _update_history_status(task_id, "completed", str(output_path), output_size)

    except Exception as e:
        import traceback
        traceback.print_exc()
        with tasks_lock:
            tasks_store[task_id]["status"] = "failed"
            tasks_store[task_id]["error"] = str(e)
            tasks_store[task_id]["phase"] = "Failed"
        _update_history_status(task_id, "failed")


@app.get("/api/categories")
async def get_categories():
    return {"categories": FORMAT_CATEGORIES}


@app.get("/api/formats")
async def get_formats():
    return {"formats": registry.get_all_formats()}


@app.get("/api/compatible/{source_ext}")
async def get_compatible_formats(source_ext: str):
    return {"source": source_ext, "targets": _get_compatible_formats(source_ext)}


@app.get("/api/path")
async def get_conversion_path(src: str, target: str):
    path = engine.find_path(src, target)
    if path is None:
        raise HTTPException(status_code=404, detail=f"No conversion path from {src} to {target}")
    steps = [PathStep(source=c.source_format, target=c.target_format) for c in path]
    return PathResponse(path=steps, total_steps=len(steps))


@app.get("/api/presets")
async def get_presets():
    return {"presets": DEVICE_PRESETS}


@app.post("/api/convert")
async def convert_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_format: str = Form(...),
    options: str = Form(None)
):
    filename = file.filename or "uploaded_file"
    task_id = str(uuid.uuid4())

    parsed_options = {}
    if options:
        try:
            parsed_options = json.loads(options)
        except Exception:
            parsed_options = {}

    input_path = uploads_dir / f"{task_id}_{filename}"
    final_filename = f"converted_{Path(filename).stem}.{target_format}"
    output_path = downloads_dir / final_filename

    try:
        content = await file.read()
        input_size = len(content)

        with input_path.open("wb") as f:
            f.write(content)

        with tasks_lock:
            tasks_store[task_id] = {
                "task_id": task_id,
                "filename": filename,
                "target": target_format,
                "timestamp": time.time(),
                "status": "uploading",
                "progress": 100,
                "phase": "Uploaded",
                "input_path": str(input_path),
                "input_size": input_size,
                "input_size_fmt": _format_size(input_size),
                "output_path": None,
                "output_size": 0,
                "output_size_fmt": "",
                "error": None,
            }

        _add_history(task_id, filename, target_format, "uploaded", input_size)
        background_tasks.add_task(_run_conversion, task_id, input_path, target_format, output_path, parsed_options)

        return {
            "task_id": task_id,
            "filename": filename,
            "input_size": input_size,
            "input_size_fmt": _format_size(input_size),
            "status": "uploaded"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    with tasks_lock:
        task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": task["task_id"],
        "status": task["status"],
        "progress": task.get("progress", 0),
        "phase": task.get("phase", ""),
        "filename": task["filename"],
        "target": task["target"],
        "input_size_fmt": task.get("input_size_fmt", ""),
        "output_size_fmt": task.get("output_size_fmt", ""),
        "error": task.get("error"),
    }


@app.get("/api/download/{task_id}")
async def download_result(task_id: str):
    with tasks_lock:
        task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Conversion not completed")

    output_path = Path(task["output_path"])
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    download_name = f"{Path(task['filename']).stem}.{task['target']}"
    return FileResponse(
        path=output_path,
        filename=download_name,
        media_type="application/octet-stream"
    )


@app.post("/api/convert-batch")
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

        content = await file.read()
        input_size = len(content)

        with input_path.open("wb") as f:
            f.write(content)

        with tasks_lock:
            tasks_store[task_id] = {
                "task_id": task_id,
                "filename": filename,
                "target": target_format,
                "timestamp": time.time(),
                "status": "uploading",
                "progress": 100,
                "phase": "Uploaded",
                "batch_id": batch_id,
                "input_path": str(input_path),
                "input_size": input_size,
                "input_size_fmt": _format_size(input_size),
                "output_path": None,
                "output_size": 0,
                "output_size_fmt": "",
                "error": None,
            }

        _add_history(task_id, filename, target_format, "uploaded", input_size)
        background_tasks.add_task(_run_conversion, task_id, input_path, target_format, output_path, parsed_options)
        task_ids.append(task_id)

    return {"batch_id": batch_id, "task_ids": task_ids, "task_count": len(task_ids)}


@app.get("/api/batch-status/{batch_id}")
async def get_batch_status(batch_id: str):
    with tasks_lock:
        batch_tasks = [t for t in tasks_store.values() if t.get("batch_id") == batch_id]

    if not batch_tasks:
        raise HTTPException(status_code=404, detail="Batch not found")

    completed = sum(1 for t in batch_tasks if t["status"] == "completed")
    failed = sum(1 for t in batch_tasks if t["status"] == "failed")
    total = len(batch_tasks)

    tasks_info = []
    for t in batch_tasks:
        tasks_info.append({
            "task_id": t["task_id"],
            "filename": t["filename"],
            "status": t["status"],
            "progress": t.get("progress", 0),
            "phase": t.get("phase", ""),
        })

    return {
        "batch_id": batch_id,
        "total": total,
        "completed": completed,
        "failed": failed,
        "progress": (completed / total * 100) if total else 0,
        "tasks": tasks_info
    }


@app.get("/api/batch-zip/{batch_id}")
async def download_batch_zip(batch_id: str):
    with tasks_lock:
        batch_tasks = [t for t in tasks_store.values() if t.get("batch_id") == batch_id]

    completed = [t for t in batch_tasks if t["status"] == "completed" and t.get("output_path")]
    if not completed:
        raise HTTPException(status_code=400, detail="No completed files to download")

    zip_path = downloads_dir / f"batch_{batch_id}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for t in completed:
            out = Path(t["output_path"])
            if out.exists():
                arcname = f"{Path(t['filename']).stem}.{t['target']}"
                zf.write(out, arcname)

    return FileResponse(
        path=zip_path,
        filename=f"converted_{batch_id[:8]}.zip",
        media_type="application/zip"
    )


@app.post("/api/tool/execute")
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
        content = await file.read()
        with path.open("wb") as f:
            f.write(content)
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
            "status": "uploading",
            "progress": 100,
            "phase": "Uploaded",
            "input_path": str(primary_input),
            "input_size": primary_input.stat().st_size,
            "input_size_fmt": _format_size(primary_input.stat().st_size),
            "output_path": None,
            "output_size": 0,
            "output_size_fmt": "",
            "error": None,
        }

    _add_history(task_id, primary_input.name, target_format, "uploaded", primary_input.stat().st_size)
    background_tasks.add_task(_run_conversion, task_id, primary_input, target_format, output_path, parsed_options, tool_id=tool_id)

    return {"task_id": task_id, "status": "uploaded"}


@app.websocket("/ws/status/{task_id}")
async def websocket_status(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        while True:
            with tasks_lock:
                task = tasks_store.get(task_id)
            if not task:
                await websocket.send_json({"status": "failed", "progress": 0, "phase": "Not found"})
                break
            await websocket.send_json({
                "status": task["status"],
                "progress": task.get("progress", 0),
                "phase": task.get("phase", ""),
                "output_size_fmt": task.get("output_size_fmt", ""),
            })
            if task["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(0.3)
    except WebSocketDisconnect:
        pass


@app.get("/api/history")
async def get_history():
    with tasks_lock:
        return {"history": list(history_store[:20])}


@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("app/templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, workers=1, timeout_keep_alive=5)
