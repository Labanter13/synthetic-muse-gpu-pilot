"""Synthetic Muse Kandinsky 6 Lite Distill — one-job self-hosted GPU pilot.

NOTICE: No model weights are in the Docker image. They download on the first job.
The HTTPS gateway may be public: all job/content endpoints require PILOT_API_KEY.
"""
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
from PIL import Image, ImageOps
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("muse-kandinsky")
app = FastAPI(title="Synthetic Muse Kandinsky 6 Pilot", docs_url=None, redoc_url=None)
MODEL_ID = "kandinskylab/Kandinsky-6.0-Lite-distill-5s-Diffusers"
PORT = int(os.environ.get("PORT", "8000"))
KEY = os.environ.get("PILOT_API_KEY", "")
OUT = Path("/tmp/kandinsky-pilot-output")
OUT.mkdir(parents=True, exist_ok=True)
LOCK = threading.Lock()
STATE = dict(job_id=None, status="idle", stage="idle", error=None,
             elapsed_seconds=None, started_at=None, video_path=None)
PIPE = None

def auth(key: str):
    if len(KEY) < 24:
        raise HTTPException(503, "PILOT_API_KEY must be configured: at least 24 characters")
    if not key or not secrets.compare_digest(key, KEY):
        raise HTTPException(401, "Invalid API key")

def snapshot():
    with LOCK:
        return {k: v for k, v in STATE.items() if k != "video_path"}

def update(**kwargs):
    with LOCK:
        STATE.update(kwargs)
    LOG.info("KANDINSKY_STAGE %s", json.dumps({k: v for k, v in kwargs.items() if k != "video_path"}))

def monitor_model_cache(done: threading.Event, started: float):
    """Bounded, read-only download progress logs; no secrets or model contents exposed."""
    cache = Path(os.environ.get("HF_HOME", "/tmp/huggingface"))
    previous_mb = None
    while not done.is_set():
        files = 0
        total_bytes = 0
        try:
            # Count actual files rather than assuming the checkpoint's advertised size.
            # The Hugging Face cache can also include partially downloaded .incomplete files.
            for base, _, names in os.walk(cache):
                for name in names:
                    path = os.path.join(base, name)
                    if not os.path.islink(path):
                        try:
                            total_bytes += os.stat(path).st_size
                            files += 1
                        except OSError:
                            continue
            cache_mb = total_bytes / (1024 ** 2)
            free_gb = shutil.disk_usage("/tmp").free / (1024 ** 3)
            delta = None if previous_mb is None else round(cache_mb - previous_mb, 1)
            LOG.info(
                "KANDINSKY_DOWNLOAD_PROGRESS elapsed_sec=%d cache_mb=%.1f delta_mb=%s "
                "files=%d free_disk_gb=%.1f",
                int(time.monotonic() - started), cache_mb, delta,
                files, free_gb
            )
            previous_mb = cache_mb
        except Exception:
            LOG.exception("KANDINSKY_DOWNLOAD_PROGRESS probe_failed")
        done.wait(60)


def get_pipe():
    global PIPE
    if PIPE is None:
        import torch
        from diffusers import Kandinsky6TI2VAPipeline
        if not torch.cuda.is_available():
            raise RuntimeError("NVIDIA CUDA GPU unavailable")
        free_gb = shutil.disk_usage("/tmp").free / 1024**3
        if free_gb < 40:
            raise RuntimeError(f"Insufficient free disk ({free_gb:.1f} GB); need at least 40 GB for model download/cache")
        LOG.info("KANDINSKY_STAGE model_download_begin model=%s free_disk_gb=%.1f", MODEL_ID, free_gb)
        t0 = time.monotonic()
        finish_monitor = threading.Event()
        telemetry = threading.Thread(target=monitor_model_cache, args=(finish_monitor, t0), daemon=True)
        telemetry.start()
        try:
            pipe = Kandinsky6TI2VAPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.bfloat16)
            pipe.enable_model_cpu_offload()
            pipe.vae.enable_tiling()
            PIPE = pipe
            LOG.info("KANDINSKY_STAGE model_ready seconds=%.1f", time.monotonic()-t0)
        finally:
            finish_monitor.set()
    return PIPE

def work(job_id: str, photo: bytes, prompt: str, seed: int, with_audio: bool):
    t0 = time.monotonic()
    try:
        import torch
        from diffusers.utils import encode_video, export_to_video
        update(status="running", stage="loading_model")
        pipe = get_pipe()
        with Image.open(io.BytesIO(photo)) as original:
            portrait = ImageOps.fit(ImageOps.exif_transpose(original).convert("RGB"),
                                    (480, 864), method=Image.Resampling.LANCZOS)
        LOG.info("KANDINSKY_STAGE input_ready width=480 height=864 steps=10 seed=%s audio=%s", seed, with_audio)
        update(stage="generating")
        result = pipe(
            prompt=prompt,
            image=portrait,
            height=864,
            width=480,
            num_frames=121,
            num_inference_steps=10,
            guidance_scale=1.0,
            sample_audio=with_audio,
            expand_prompts=False,
            generator=torch.Generator(device="cpu").manual_seed(seed),
        )
        update(stage="encoding_mp4")
        destination = OUT / f"{job_id}.mp4"
        if with_audio:
            if result.audio is None:
                raise RuntimeError("Kandinsky returned no audio even though audio generation was enabled")
            # Kandinsky returns mono waveforms: encode_video muxes audio with video in one MP4.
            waveform = torch.as_tensor(result.audio[0], dtype=torch.float32).reshape(1, -1).cpu()
            if waveform.numel() == 0:
                raise RuntimeError("Kandinsky returned an empty audio waveform")
            encode_video(result.frames[0], fps=24, output_path=str(destination),
                         audio=waveform, audio_sample_rate=pipe.audio_sample_rate)
            LOG.info("KANDINSKY_STAGE audio_encoded samples=%s rate=%s",
                     waveform.shape[-1], pipe.audio_sample_rate)
        else:
            export_to_video(result.frames[0], str(destination), fps=24)
        if not destination.exists() or destination.stat().st_size < 4096:
            raise RuntimeError("MP4 encoder returned an empty or invalid file")
        duration = round(time.monotonic()-t0, 1)
        update(status="completed", stage="ready_to_download",
               video_path=str(destination), elapsed_seconds=duration)
        LOG.info("KANDINSKY_RESULT success job=%s elapsed_sec=%s size_bytes=%s",
                 job_id, duration, destination.stat().st_size)
    except Exception as exc:
        LOG.exception("KANDINSKY_RESULT failure job=%s", job_id)
        update(status="failed", stage="failed", error=str(exc)[:700],
               elapsed_seconds=round(time.monotonic()-t0, 1))

@app.get("/")
def index():
    return HTMLResponse((Path("/app/index.html")).read_text(encoding="utf-8"),
                        headers={"Cache-Control": "no-store"})

@app.get("/health")
def health():
    try:
        import torch
        return {"status": "running", "cuda": torch.cuda.is_available(),
                "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                "configured": len(KEY)>=24, "model": MODEL_ID}
    except Exception as exc:
        return {"status": "startup_error", "message": str(exc)[:200]}

@app.get("/job")
def job(x_api_key: str = Header(default="")):
    auth(x_api_key)
    return snapshot()

@app.post("/generate")
async def generate(image: UploadFile = File(...),
                   prompt: str = Form(...), seed: int = Form(42),
                   with_audio: bool = Form(True),
                   x_api_key: str = Header(default="")):
    auth(x_api_key)
    if not 10 <= len(prompt) <= 1500:
        raise HTTPException(400, "Prompt length must be between 10 and 1500 characters")
    if not 0 <= seed <= 2147483647:
        raise HTTPException(400, "Invalid seed")
    raw = await image.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:
        raise HTTPException(413, "Image exceeds 8 MB")
    try:
        with Image.open(io.BytesIO(raw)) as img:
            img.verify()
    except Exception:
        raise HTTPException(400, "Only valid JPEG or PNG images are accepted")
    with LOCK:
        if STATE["status"] in ("queued", "running"):
            raise HTTPException(409, "Another generation is already running")
        new_id = secrets.token_hex(8)
        STATE.update(job_id=new_id, status="queued", stage="queued", with_audio=with_audio,
                     error=None, elapsed_seconds=None,
                     video_path=None, started_at=time.time())
    threading.Thread(target=work, args=(new_id, raw, prompt, seed, with_audio),
                     daemon=True).start()
    return {"job_id": new_id, "status": "queued"}

@app.get("/download/{job_id}")
def download(job_id: str, x_api_key: str = Header(default="")):
    auth(x_api_key)
    with LOCK:
        if STATE["job_id"] != job_id or STATE["status"] != "completed":
            raise HTTPException(404, "Output not available")
        destination = STATE["video_path"]
    return FileResponse(destination, media_type="video/mp4",
                        filename="synthetic-muse-kandinsky-test.mp4")

if __name__ == "__main__":
    try:
        import torch
        LOG.info("KANDINSKY_BOOT cuda=%s gpu=%s",
                 torch.cuda.is_available(),
                 torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none")
    except Exception:
        LOG.exception("KANDINSKY_BOOT torch_load_error")
    LOG.info("KANDINSKY_BOOT configured=%s", len(KEY)>=24)
    uvicorn.run(app, host="::", port=PORT, log_level="info")
