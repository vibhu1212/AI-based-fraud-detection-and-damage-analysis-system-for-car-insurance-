FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for OCR and CV
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Install poetry (optional, but good practice if we use it later)
# RUN pip install poetry

# Copy dummy requirements for now
# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Placeholder command
CMD ["python", "-c", "print('Backend is running')"]
