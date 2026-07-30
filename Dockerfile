FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic-dev \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p downloads

EXPOSE 8000

CMD ["python", "-m", "app.main"]
