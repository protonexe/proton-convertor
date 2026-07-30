# Proton Convertor

**Proton Convertor** is a professional-grade, universal file conversion engine designed to handle virtually any file format in existence. By utilizing a graph-based routing system and universal "hubs," it enables seamless conversion across completely different file categories (e.g., converting a YAML file to an MP4 video).

## Key Features

- **Universal Connectivity**: Convert between any two formats. If a direct path doesn't exist, the engine automatically finds the shortest path through "hub" formats.
- **Omni-Converter Fallback**: No file is unconvertible. Esoteric or niche extensions are automatically routed via binary-to-base64 or UTF-8 text bridges.
- **Cross-Category Bridges**:
  - Documents to Images: PDF to PNG/JPG and vice versa.
  - Images to Media: Static images to 1s videos and video frames to images.
  - Data to Documents: JSON/CSV/YAML to Markdown/HTML/PDF.
- **Modern UI**: A sleek, responsive single-page interface built with Tailwind CSS and JS.
- **Professional Backend**: High-performance processing using FFmpeg, PyMuPDF, and Pillow.
- **No External Services**: Runs standalone without Redis or Celery.

## Architecture

Proton Convertor uses a **Conversion Graph**:
1. **Nodes**: File extensions.
2. **Edges**: Converter adapters.
3. **Pathfinding**: When a user requests a conversion, the engine uses **Breadth-First Search (BFS)** to find the most efficient route from the source to the target format.

### Format Families
- **Images**: PNG, JPG, WEBP, BMP, GIF, TIFF, ICO, EPS.
- **Media**: MP3, WAV, OGG, M4A, FLAC, AAC, MP4, AVI, MKV, MOV, WEBM.
- **Documents**: PDF, TXT, MD, HTML, DOCX.
- **Data**: JSON, CSV, YAML, XML, XLSX.

## Quick Start

### Prerequisites
- Python 3.11+
- FFmpeg (for media conversions)

### Installation
```bash
git clone https://github.com/protonexe/proton-convertor.git
cd proton-convertor
pip install -r requirements.txt
```

### Running the App
```bash
python -m app.main
```
Open your browser to `http://localhost:8000`.

## Deployment (Docker)
```bash
docker build -t proton-convertor .
docker run -p 8000:8000 proton-convertor
```

## Tools
- **PDF Tools**: Merge, split, rotate PDFs
- **Audio Tools**: Trim, merge, adjust volume
- **Compression**: Optimize images, videos, and audio files
- **OCR**: Extract text from images using Tesseract

## License
MIT License

---
made with love by [proton](https://github.com/protonexe)
