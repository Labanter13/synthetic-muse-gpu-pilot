"""Encode lossless pipeline frames to a visually high-quality H.264 MP4.

ffmpeg is used directly rather than diffusers export_to_video(quality=5) or
PyAV encode_video() defaults, which yielded low-bitrate 480p pilot clips.
This improves retained detail, NOT the native generated resolution.
"""
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np


def encode_quality_mp4(frames, destination, fps=24, audio=None, audio_sample_rate=44100):
    if not frames:
        raise ValueError("Cannot encode an empty video")
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = frames[0].size
    if (width % 2) or (height % 2):
        raise ValueError("Video width and height must be even for yuv420p")
    with tempfile.TemporaryDirectory(prefix="kandinsky-encode-") as tmp:
        args = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s:v", f"{width}x{height}", "-r", str(fps), "-i", "pipe:0",
        ]
        if audio is not None:
            if hasattr(audio, "detach"):
                audio = audio.detach().float().cpu().numpy()
            mono = np.asarray(audio, dtype=np.float32).reshape(-1)
            if mono.size == 0:
                raise ValueError("Requested audio is empty")
            if not np.isfinite(mono).all():
                raise ValueError("Audio contains NaN or infinity")
            audio_file = str(Path(tmp) / "audio.wav")
            pcm = (np.clip(mono, -1.0, 1.0) * 32767.0).astype("<i2")
            with wave.open(audio_file, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(int(audio_sample_rate))
                wav.writeframes(pcm.tobytes())
            args += ["-i", audio_file]
        args += ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p"]
        if audio is None:
            args += ["-an"]
        else:
            args += ["-c:a", "aac", "-b:a", "192k"]
        args += ["-movflags", "+faststart", str(path)]
        proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE)
        try:
            for frame in frames:
                if frame.size != (width, height):
                    raise ValueError("Inconsistent frame dimensions")
                proc.stdin.write(frame.convert("RGB").tobytes())
        except Exception:
            proc.kill()
            proc.wait()
            raise
        finally:
            if proc.stdin is not None:
                proc.stdin.close()
        error = proc.stderr.read().decode("utf-8", errors="replace")[-1500:]
        return_code = proc.wait()
        if return_code != 0:
            raise RuntimeError(f"ffmpeg video encode failed (exit {return_code}): {error}")
    if not path.exists() or path.stat().st_size < 1024:
        raise RuntimeError("Output MP4 missing or empty")
    return path
