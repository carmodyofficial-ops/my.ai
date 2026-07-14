#!/usr/bin/env python3
"""Kokoro-82M TTS sidecar — OpenAI-compatible /v1/audio/speech on loopback.

Why a sidecar: the odysseus container runs Python 3.14 where kokoro's
misaki→spacy dependency has no wheels; the host python (3.12) installs it
cleanly. The app consumes this through its EXISTING endpoint provider
(`tts_provider = "endpoint:<model-endpoint-id>"` → POST {base_url}/audio/speech),
so no core Odysseus code depends on this file.

Run (deploy/myai-tts-sidecar.service, or by hand):
    ~/myai-tts/venv/bin/python scripts/wearables/tts_sidecar.py
Binds 127.0.0.1:8123 only — the container reaches it via host.docker.internal;
it is never exposed to the LAN. Returns WAV bytes regardless of the requested
response_format (the callers detect the container format from magic bytes).
"""

from __future__ import annotations

import io
import logging
import threading
import wave

import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tts-sidecar")

# Default bind is loopback; the systemd unit sets the docker-bridge IP
# (172.17.0.1) so the odysseus container reaches it via host.docker.internal —
# same posture as the myai-ollama-bridge-proxy. Neither address is
# LAN-routable.
import os
HOST = os.environ.get("MYAI_TTS_BIND_HOST", "127.0.0.1")
PORT = int(os.environ.get("MYAI_TTS_BIND_PORT", "8123"))
SAMPLE_RATE = 24_000
MAX_CHARS = 4000
DEFAULT_VOICE = "af_heart"

app = FastAPI(title="myai-tts-sidecar")
_pipeline = None
_lock = threading.Lock()  # kokoro pipeline is not proven thread-safe


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        from kokoro import KPipeline
        log.info("loading Kokoro-82M (cpu)...")
        _pipeline = KPipeline(lang_code="a", device="cpu")
        log.info("Kokoro loaded")
    return _pipeline


class SpeechRequest(BaseModel):
    model: str = "kokoro"
    input: str
    voice: str = DEFAULT_VOICE
    response_format: str = "mp3"  # accepted, but WAV is always returned
    speed: float = 1.0


@app.get("/health")
def health():
    return {"ok": True, "service": "myai-tts-sidecar", "voice_default": DEFAULT_VOICE}


@app.post("/v1/audio/speech")
def speech(req: SpeechRequest):
    text = (req.input or "").strip()
    if not text:
        raise HTTPException(400, "input required")
    if len(text) > MAX_CHARS:
        raise HTTPException(413, f"input exceeds {MAX_CHARS} chars")
    voice = req.voice if (req.voice or "").startswith(("af_", "am_", "bf_", "bm_")) \
        else DEFAULT_VOICE
    speed = min(max(req.speed or 1.0, 0.5), 2.0)
    with _lock:
        pipe = get_pipeline()
        chunks = []
        for _, _, audio in pipe(text, voice=voice, speed=speed):
            a = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
            chunks.append(a)
    if not chunks:
        raise HTTPException(500, "synthesis produced no audio")
    full = np.concatenate(chunks)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes((np.clip(full, -1, 1) * 32767).astype(np.int16).tobytes())
    data = buf.getvalue()
    log.info("synthesized %d chars -> %d bytes (voice=%s)", len(text), len(data), voice)
    from fastapi.responses import Response
    return Response(content=data, media_type="audio/wav")


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
