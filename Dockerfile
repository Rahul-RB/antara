FROM python:3.12-slim

# System deps for OpenCV, pillow-heif, and InsightFace/ONNX
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libheif1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .

# Persistent volumes for the SQLite DB and downloaded images
VOLUME ["/app/antara.db", "/app/images"]

ENV FLASK_SECRET_KEY="some-dummy-session-key"

EXPOSE 5000

CMD ["python3", "app.py"]
