"""Synthetic Muse Video Pilot v0.1: non-explicit research image-to-video."""
import io
import json
import logging
import os
import secrets
import shutil
import threading
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from PIL import Image, ImageFilter, ImageOps
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("synthetic-muse-video")
app = FastAPI(title="Synthetic Muse Video Pilot", docs_url=None, redoc_url=None)
PORT = int(os.environ.get("PORT", "8000"))
OUTPUT_DIR = Path("/tmp/video-pilot-outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_ID = os.environ.get("MODEL_ID", "stabilityai/stable-video-diffusion-img2vid")
KEY = os.environ.get("PILOT_API_KEY", "")
STATE_LOCK = threading.Lock()
STATE = {"job_id": None, "status": "idle", "stage": "idle", "error": None,
         "elapsed_seconds": None, "video_path": None, "started_at": None}
PIPE = None

def require_key(x_api_key):
    if len(KEY) < 24:
        raise HTTPException(503, "Server requires PILOT_API_KEY (24+ characters) as a private environment variable")
    if not x_api_key or not secrets.compare_digest(x_api_key, KEY):
        raise HTTPException(401, "Invalid API key")

def set_state(**updates):
    with STATE_LOCK:
        STATE.update(updates)
    LOG.info("PILOT_STAGE %s", json.dumps({k: v for k, v in updates.items() if k != "video_path"}))

def clean_status():
    with STATE_LOCK:
        return {k: v for k, v in STATE.items() if k != "video_path"}

def portrait_to_landscape(img):
    """Preserve a portrait image using a blurred 1024x576 background rather than cropping the face."""
    img = ImageOps.exif_transpose(img).convert("RGB")
    bg = ImageOps.fit(img, (1024, 576), method=Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=36))
    fg = ImageOps.contain(img, (1024, 576), method=Image.Resampling.LANCZOS)
    bg.paste(fg, ((1024-fg.width)//2, (576-fg.height)//2))
    return bg

def get_pipeline():
    global PIPE
    if PIPE is None:
        import torch
        from diffusers import StableVideoDiffusionPipeline
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA GPU not available inside container")
        LOG.info("PILOT_STAGE model_load_begin id=%s gpu=%s", MODEL_ID, torch.cuda.get_device_name(0))
        started = time.monotonic()
        PIPE = StableVideoDiffusionPipeline.from_pretrained(
            MODEL_ID, torch_dtype=torch.float16, variant="fp16"
        )
        PIPE.enable_model_cpu_offload()
        PIPE.unet.enable_forward_chunking()
        LOG.info("PILOT_STAGE model_loaded seconds=%.1f", time.monotonic()-started)
    return PIPE

def run_job(job_id, image_bytes, steps, motion):
    started = time.monotonic()
    try:
        from diffusers.utils import export_to_video
        import torch
        set_state(status="running", stage="loading_model")
        pipe = get_pipeline()
        set_state(stage="generating")
        with Image.open(io.BytesIO(image_bytes)) as raw:
            image = portrait_to_landscape(raw)
        generator = torch.Generator(device="cpu").manual_seed(42)
        result = pipe(image, num_frames=14, num_inference_steps=steps,
                      decode_chunk_size=1, motion_bucket_id=motion,
                      noise_aug_strength=0.02, generator=generator)
        set_state(stage="encoding_mp4")
        video = OUTPUT_DIR / (job_id + ".mp4")
        export_to_video(result.frames[0], str(video), fps=7)
        if not video.exists() or video.stat().st_size < 4096:
            raise RuntimeError("Video encoder did not produce a valid MP4")
        set_state(status="completed", stage="ready_to_download",
                  video_path=str(video), elapsed_seconds=round(time.monotonic()-started, 1))
        LOG.info("PILOT_RESULT success job=%s bytes=%d", job_id, video.stat().st_size)
    except Exception as exc:
        LOG.exception("PILOT_RESULT failed job=%s", job_id)
        set_state(status="failed", stage="failed", error=str(exc)[:500],
                  elapsed_seconds=round(time.monotonic()-started, 1))

@app.get("/health")
def health():
    try:
        import torch
        return {"service": "synthetic-muse-video-pilot", "status": "running",
                "gpu_visible": torch.cuda.is_available(),
                "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                "model": MODEL_ID, "configured": len(KEY) >= 24}
    except Exception as exc:
        return {"status": "error", "message": str(exc)[:100]}

@app.get("/")
def index():
    return HTMLResponse(Path("/app/index.html").read_text(encoding="utf-8"))

@app.get("/job")
def status(x_api_key: str = Header(default="")):
    require_key(x_api_key)
    return clean_status()

@app.post("/generate")
async def generate(image: UploadFile = File(...), steps: int = Form(16),
                   motion: int = Form(90), x_api_key: str = Header(default="")):
    require_key(x_api_key)
    if not 8 <= steps <= 30 or not 1 <= motion <= 200:
        raise HTTPException(400, "Steps must be 8-30 and motion 1-200")
    b = await image.read(8 * 1024 * 1024 + 1)
    if len(b) > 8 * 1024 * 1024:
        raise HTTPException(413, "Image larger than 8 MB")
    try:
        with Image.open(io.BytesIO(b)) as img:
            img.verify()
    except Exception:
        raise HTTPException(400, "Upload a valid JPG or PNG")
    with STATE_LOCK:
        if STATE["status"] in ("queued", "running"):
            raise HTTPException(409, "A generation is already in progress")
        job_id = secrets.token_hex(8)
        STATE.update(job_id=job_id, status="queued", stage="queued", error=None,
                     elapsed_seconds=None, video_path=None, started_at=time.time())
    threading.Thread(target=run_job, args=(job_id, b, steps, motion), daemon=True).start()
    return {"job_id": job_id, "status": "queued"}

@app.get("/download/{job_id}")
def download(job_id: str, x_api_key: str = Header(default="")):
    require_key(x_api_key)
    with STATE_LOCK:
        if STATE["job_id"] != job_id or STATE["status"] != "completed":
            raise HTTPException(404, "Video not ready")
        path = STATE["video_path"]
    return FileResponse(path, media_type="video/mp4", filename="synthetic-muse-pilot.mp4")

if __name__ == "__main__":
    try:
        import torch
        LOG.info("PILOT_BOOT GPU=%s", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NOT_VISIBLE")
    except Exception:
        LOG.exception("PILOT_BOOT torch_gpu_probe_failed")
    LOG.info("PILOT_BOOT configured_api_key=%s", len(KEY) >= 24)
    uvicorn.run(app, host="::", port=PORT, log_level="info")
