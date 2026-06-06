# Use a lightweight Python image
FROM python:3.11-slim

# Install system dependencies (FFmpeg is required for media conversion)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic-dev \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create the downloads directory for converted files
RUN mkdir -p downloads

# Expose the port FastAPI runs on
EXPOSE 8000

# Start the application
CMD ["python", "-m", "app.main"]
