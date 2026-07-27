# Enterprise Multi-Stage Dockerfile for FaceGuard Facial Auth
FROM python:3.11-slim as builder

# Install build & system dependencies for OpenCV and MediaPipe
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements & install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final runtime image
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Non-root security user
RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

# Set data storage permissions
RUN mkdir -p data/face_encodings data/logs /tmp && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "wsgi:app"]
