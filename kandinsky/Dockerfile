# Synthetic Muse Kandinsky 6 Lite Distill — paid GPU only used at runtime.
# No pretrained weights or private content are included in this public image.
FROM nvidia/cuda:12.8.1-runtime-ubuntu24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
ENV HF_HOME=/tmp/huggingface HF_HUB_DISABLE_TELEMETRY=1 PORT=8000 OMP_NUM_THREADS=4
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv ffmpeg ca-certificates libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
# Install CUDA-enabled PyTorch without needing an NVIDIA GPU on the CI runner.
RUN python3 -m pip install --break-system-packages --no-cache-dir \
    torch==2.9.1 torchvision==0.24.1 --index-url https://download.pytorch.org/whl/cu128
COPY kandinsky/requirements.txt /app/requirements.txt
RUN python3 -m pip install --break-system-packages --no-cache-dir -r /app/requirements.txt
COPY kandinsky/server.py /app/server.py
COPY kandinsky/index.html /app/index.html
RUN test -s /app/index.html && python3 -m py_compile /app/server.py \
    && python3 -c "import av; from diffusers import Kandinsky6TI2VAPipeline; from diffusers.utils import encode_video; print('KANDINSKY_AUDIO_IMPORT_OK', flush=True)" \
    && python3 -c "from diffusers.utils import encode_video; from PIL import Image; import torch; encode_video([Image.new('RGB', (32, 32), 'black') for _ in range(3)], fps=24, output_path='/tmp/audio-smoke.mp4', audio=torch.zeros((1, 5512)), audio_sample_rate=44100)" \
    && ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1 /tmp/audio-smoke.mp4 | grep -q aac
EXPOSE 8000
CMD ["python3", "-u", "/app/server.py"]
