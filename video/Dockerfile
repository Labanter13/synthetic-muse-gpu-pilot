# Synthetic Muse Video Pilot 0.1 — experimental, SVD image-to-video (non-explicit only)
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip python3-venv ffmpeg ca-certificates libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN python3 -m pip install --upgrade pip && python3 -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu121
COPY video/requirements.txt /app/requirements.txt
RUN python3 -m pip install -r /app/requirements.txt
COPY video/server.py /app/server.py
ENV PORT=8000 HF_HOME=/tmp/huggingface MODEL_ID=stabilityai/stable-video-diffusion-img2vid
EXPOSE 8000
CMD ["python3", "-u", "/app/server.py"]
