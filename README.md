# ⚛️ Proton Convertor

**Proton Convertor** is a professional-grade, universal file conversion engine designed to handle virtually any file format in existence. By utilizing a graph-based routing system and universal "hubs," it enables seamless conversion across completely different file categories (e.g., converting a YAML file to an MP4 video).

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)

## ✨ Key Features

- **Universal Connectivity**: Convert between any two formats. If a direct path doesn't exist, the engine automatically finds the shortest path through "hub" formats.
- **Omni-Converter Fallback**: No file is unconvertible. Esoteric or niche extensions are automatically routed via binary-to-base64 or UTF-8 text bridges.
- **Cross-Category Bridges**:
  - 📄 **Documents $\leftrightarrow$ 🖼️ Images**: PDF to PNG/JPG and vice versa.
  - 🖼️ **Images $\leftrightarrow$ 🎬 Media**: Static images to 1s videos and video frames to images.
  - 📊 **Data $\leftrightarrow$ 📄 Documents**: JSON/CSV/YAML to Markdown/HTML/PDF.
- **Modern UI**: A sleek, responsive single-page interface built with Tailwind CSS and JS.
- **Professional Backend**: High-performance processing using `FFmpeg`, `PyMuPDF`, and `Pillow`.

## 🛠️ Architecture

Proton Convertor doesn't use static conversion pairs. Instead, it uses a **Conversion Graph**:
1. **Nodes**: File extensions.
2. **Edges**: Converter adapters.
3. **Pathfinding**: When a user requests a conversion, the engine uses a **Breadth-First Search (BFS)** to find the most efficient route from the source to the target format.

### Format Families
- **Images**: PNG, JPG, WEBP, BMP, GIF, TIFF, ICO, EPS.
- **Media**: MP3, WAV, OGG, M4A, FLAC, MP4, AVI, MKV, MOV, WEBM.
- **Documents**: PDF, TXT, MD, HTML.
- **Data**: JSON, CSV, YAML, XML.

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.11+
- [FFmpeg](https://ffmpeg.org/download.html) (Must be installed and added to your system PATH for media conversions).

### Installation
```bash
# Clone the repository
git clone https://github.com/protonexe/proton-convertor.git
cd proton-convertor

# Install dependencies
pip install -r requirements.txt
```

### Running the App
```bash
python -m app.main
```
Open your browser to `http://localhost:8000`.

## ☁️ Deployment (Render/Cloud)

This project is fully containerized. To deploy:
1. Connect your GitHub repo to [Render](https://render.com).
2. Select **Web Service**.
3. Set the **Runtime** to **Docker**.
4. Deploy.

## 📜 License
Distributed under the MIT License.

---
made with ❤️ by [proton](https://github.com/protonexe)
