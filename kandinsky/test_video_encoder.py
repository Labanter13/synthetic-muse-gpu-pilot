"""CPU-only sanity check: the container can generate MP4 with and without AAC sound."""
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from video_encoder import encode_quality_mp4

with tempfile.TemporaryDirectory() as temp:
    frames = [Image.new("RGB", (64, 64), (90 + 15 * i, 25, 90)) for i in range(8)]
    for with_audio in (False, True):
        filename = Path(temp) / ("with-audio.mp4" if with_audio else "silent.mp4")
        waveform = np.sin(np.arange(22050, dtype=np.float32) / 44100 * 440 * 2 * np.pi) * 0.1
        encode_quality_mp4(frames, filename, fps=24,
                           audio=waveform if with_audio else None, audio_sample_rate=44100)
        cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name",
               "-of", "json", str(filename)]
        streams = json.loads(subprocess.check_output(cmd, text=True))["streams"]
        video_count = sum(s["codec_type"] == "video" for s in streams)
        audio_count = sum(s["codec_type"] == "audio" for s in streams)
        assert video_count == 1 and audio_count == int(with_audio), streams
        assert filename.stat().st_size > 1024
        print("ENCODER_SMOKE_OK", filename.name, filename.stat().st_size, streams, flush=True)
