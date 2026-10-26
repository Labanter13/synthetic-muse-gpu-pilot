#!/usr/bin/env bash
set -euo pipefail
cd /opt/kandinsky-6
if ! command -v nvidia-smi >/dev/null; then echo 'ERROR: NVIDIA GPU not visible'; exit 10; fi
nvidia-smi
# Must execute on GPU because upstream setup detects compute capability.
just setup
# Set a named RTX 4090 preset to Lite Distill, rather than silently using upstream Pro.
cp kandinsky/configs/devices/rtx-4090.yaml /tmp/synthetic-lite-4090.yaml
sed -i 's/^checkpoint: pro-distill$/checkpoint: lite-distill/' /tmp/synthetic-lite-4090.yaml
sed -i 's/^  strategy: block$/  strategy: module/' /tmp/synthetic-lite-4090.yaml
# Explicit download; first boot can transfer many GB and take substantial time.
just download lite-distill
uv pip install --python /opt/kandinsky-6/.venv/bin/python fastapi uvicorn python-multipart pillow
exec /opt/kandinsky-6/.venv/bin/python /opt/synthetic/service/api.py
