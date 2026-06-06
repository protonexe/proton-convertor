import magic
from pathlib import Path
from typing import Optional

# Map common MIME types to our internal format labels
MIME_MAP = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/bmp": "bmp",
    "image/gif": "gif",
    "image/tiff": "tiff",
    "image/x-icon": "ico",
    "audio/mpeg": "mp3",
    "audio/x-wav": "wav",
    "audio/flac": "flac",
    "audio/aac": "aac",
    "video/mp4": "mp4",
    "video/x-msvideo": "avi",
    "video/x-matroska": "mkv",
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/html": "html",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/json": "json",
    "text/csv": "csv",
    "application/x-yaml": "yaml",
    "text/yaml": "yaml",
    "application/xml": "xml",
    "text/xml": "xml",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xls",
}

def detect_format(file_path: Path) -> Optional[str]:
    """
    Detects the file format using magic bytes.
    Returns the internal format label if recognized, otherwise None.
    """
    try:
        mime = magic.from_file(str(file_path), mime=True)
        return MIME_MAP.get(mime)
    except Exception:
        return None
