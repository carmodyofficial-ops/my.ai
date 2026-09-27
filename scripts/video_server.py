#!/usr/bin/env python3
"""Local text/image-to-video job server for Wan2.2-TI2V-5B (diffusers).

Video renders take minutes, so this is a job API rather than a blocking call:

    POST /v1/videos                {prompt, quality, image_b64?}  -> {id, status}
    GET  /v1/videos/{id}           -> {status, stage, step, steps, error, ...}
    GET  /v1/videos/{id}/content   -> video/mp4

Built for a unified-memory box (GB10) shared with a resident chat model:
  * one job at a time, under a file lock shared with scripts/diffusion_server.py
    (--gpu-lock); the image server is asked to unload before each render
  * the text encoder is loaded, used and freed before the transformer loads
  * models are dropped after every job, so nothing is held between renders
  * refuses to start a job below --min-free-gb; a watchdog aborts a running job
    below --floor-gb (and hard-exits below --hard-floor-gb) instead of letting
    the box freeze

Usage:
    python3 scripts/video_server.py --base /models/Wan2.2-TI2V-5B-Diffusers \
        --turbo-transformer /models/Turbo/transformer --port 8102
"""
import argparse
import base64
import collections
import fcntl
import gc
import io
import logging
import os
import threading
import time
import urllib.request
import uuid
from pathlib import Path

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.middleware.trustedhost import TrustedHostMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("video_server")

app = FastAPI(title="Video Server")
_args = None

# quality -> (model id, steps, guidance). Turbo is CFG- and step-distilled.
QUALITY = {
    "fast": ("wan2.2-ti2v-5b-turbo", 4, 1.0),
    "high": ("wan2.2-ti2v-5b", 50, 5.0),
}
# Wan's stock negative prompt (model card); only used when CFG is on.
NEGATIVE = ("Bright tones, overexposed, static, blurred details, subtitles, style, works, paintings, "
            "images, static, overall gray, worst quality, low quality, JPEG compression residue, ugly, "
            "incomplete, extra fingers, poorly drawn hands, poorly drawn faces, deformed, disfigured, "
            "misshapen limbs, fused fingers, still picture, messy background, three legs, many people "
            "in the background, walking backwards")
# 720p landscape / portrait / square, all multiples of 32 (VAE 16x * patch 2).
SIZES = {"landscape": (1280, 704), "portrait": (704, 1280), "square": (960, 960)}
MAX_FRAMES = 121  # 5 s at 24 fps; must be 4k+1

_jobs = {}
_queue = collections.deque()
_queue_cv = threading.Condition()


class VideoRequest(BaseModel):
    prompt: str
    quality: str = "fast"
    aspect: str = "landscape"
    seconds: float = 5.0
    image_b64: str = ""
    seed: int = -1


def mem_avail_gb() -> float:
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1048576
    return -1.0


class MemoryLow(RuntimeError):
    pass


class _Watchdog(threading.Thread):
    """Samples MemAvailable while a job runs. Soft floor: the next denoise step
    raises MemoryLow. Hard floor: exit the process (systemd restarts us) — a
    lost job beats a frozen machine."""

    def __init__(self):
        super().__init__(daemon=True)
        self.low = False
        self.stop = False
        self.min_seen = 1e9

    def run(self):
        while not self.stop:
            a = mem_avail_gb()
            self.min_seen = min(self.min_seen, a)
            if a < _args.hard_floor_gb:
                logger.critical("MemAvailable %.1f GB < hard floor %.1f GB — exiting", a, _args.hard_floor_gb)
                os._exit(3)
            if a < _args.floor_gb:
                self.low = True
            time.sleep(0.25)


class _GpuLock:
    """Cross-process lock shared with diffusion_server.py so image and video
    renders never hold models in memory at the same time."""

    def __init__(self, path):
        self.path = path
        self.fd = None

    def __enter__(self):
        self.fd = open(self.path, "a+")
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        self.fd.close()


def _free():
    gc.collect()
    try:
        torch.cuda.empty_cache()
    except Exception:
        pass


def _unload_image_server():
    if not _args.image_server_url:
        return
    try:
        req = urllib.request.Request(_args.image_server_url.rstrip("/") + "/v1/unload", method="POST")
        urllib.request.urlopen(req, timeout=30).read()
        logger.info("Asked image server to unload")
    except Exception as e:
        logger.warning("Image server unload failed (continuing): %s", e)


def _frames_for(seconds: float) -> int:
    n = int(round(max(1.0, min(seconds, MAX_FRAMES / 24)) * 24))
    return min(MAX_FRAMES, (n // 4) * 4 + 1)


def _write_mp4(frames, path: Path, fps: int = 24):
    import imageio
    import numpy as np
    # H.264 / yuv420p / faststart: plays in every browser and starts streaming
    # before the whole file has downloaded.
    w = imageio.get_writer(str(path), fps=fps, codec="libx264", quality=8, pixelformat="yuv420p",
                           ffmpeg_params=["-movflags", "+faststart"], macro_block_size=16)
    try:
        for f in frames:
            w.append_data((np.clip(f, 0, 1) * 255).astype("uint8"))
    finally:
        w.close()


def _render(job):
    from diffusers import (AutoencoderKLWan, UniPCMultistepScheduler, WanImageToVideoPipeline,
                           WanPipeline, WanTransformer3DModel)

    model_id, steps, guidance = QUALITY[job["quality"]]
    width, height = SIZES[job["aspect"]]
    frames_n = _frames_for(job["seconds"])
    cfg = guidance > 1.0
    job.update(model=model_id, steps=steps, size=f"{width}x{height}", frames=frames_n)

    wd = _Watchdog()
    wd.start()
    try:
        # Stage 1: text encoder only, then free it (~11 GB back).
        job["stage"] = "encoding prompt"
        te = WanPipeline.from_pretrained(_args.base, transformer=None, vae=None,
                                         torch_dtype=torch.bfloat16).to("cuda")
        with torch.inference_mode():
            pe, ne = te.encode_prompt(job["prompt"], NEGATIVE if cfg else None, do_classifier_free_guidance=cfg,
                                      max_sequence_length=512, device="cuda", dtype=torch.bfloat16)
        del te
        _free()

        # Stage 2: transformer + VAE. bf16 VAE decode looks identical to fp32 and is ~45% faster.
        job["stage"] = "loading model"
        tf_path = _args.turbo_transformer if job["quality"] == "fast" else _args.base_transformer
        tf = WanTransformer3DModel.from_pretrained(tf_path, torch_dtype=torch.bfloat16)
        vae = AutoencoderKLWan.from_pretrained(_args.base, subfolder="vae", torch_dtype=torch.bfloat16)
        image = None
        if job.get("image_b64"):
            from PIL import Image
            image = Image.open(io.BytesIO(base64.b64decode(job["image_b64"]))).convert("RGB")
            image = image.resize((width, height), Image.LANCZOS)
            cls = WanImageToVideoPipeline
        else:
            cls = WanPipeline
        pipe = cls.from_pretrained(_args.base, text_encoder=None, tokenizer=None, transformer=tf, vae=vae,
                                   torch_dtype=torch.bfloat16).to("cuda")
        if job["quality"] == "fast":
            pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config, flow_shift=5.0)
        pipe.vae.enable_tiling()

        def on_step(p, i, t, kw):
            job["step"] = i + 1
            if i + 1 == steps:
                job["stage"] = "decoding video"  # VAE decode follows the last step
            if wd.low:
                raise MemoryLow(f"free memory fell below {_args.floor_gb} GB during the render")
            return kw

        job["stage"] = "denoising"
        seed = job["seed"] if job["seed"] >= 0 else int.from_bytes(os.urandom(4), "little")
        job["seed"] = seed
        kwargs = dict(prompt_embeds=pe, negative_prompt_embeds=ne, height=height, width=width,
                      num_frames=frames_n, num_inference_steps=steps, guidance_scale=guidance,
                      generator=torch.Generator("cuda").manual_seed(seed), callback_on_step_end=on_step)
        if image is not None:
            kwargs["image"] = image
        with torch.inference_mode():
            out = pipe(**kwargs, output_type="np")
        frames = out.frames[0]
        del pipe, tf, vae, out
        _free()

        job["stage"] = "encoding mp4"
        path = Path(_args.output_dir) / f"{job['id']}.mp4"
        _write_mp4(frames, path)
        job["file"] = str(path)
        job["min_free_gb"] = round(wd.min_seen, 1)
    finally:
        wd.stop = True
        _free()


def _worker():
    while True:
        with _queue_cv:
            while not _queue:
                _queue_cv.wait()
            job = _queue.popleft()
        job["status"] = "running"
        job["started_at"] = time.time()
        try:
            with _GpuLock(_args.gpu_lock):
                _unload_image_server()
                _free()
                avail = mem_avail_gb()
                if avail < _args.min_free_gb:
                    raise MemoryLow(f"only {avail:.1f} GB free; a 720p render needs {_args.min_free_gb:.0f} GB "
                                    "(is another large model loaded?)")
                _render(job)
            job["status"] = "done"
            job["stage"] = "done"
        except Exception as e:
            logger.exception("Job %s failed", job["id"])
            job["status"] = "failed"
            job["error"] = f"{type(e).__name__}: {e}"
        finally:
            job.pop("image_b64", None)
            job["ended_at"] = time.time()
            logger.info("Job %s %s in %.0fs", job["id"], job["status"], job["ended_at"] - job["started_at"])


def _public(job):
    keys = ("id", "status", "stage", "step", "steps", "quality", "model", "size", "frames", "seed",
            "error", "created_at", "started_at", "ended_at", "min_free_gb")
    d = {k: job.get(k) for k in keys}
    d["prompt"] = job["prompt"]
    if job["status"] == "queued":
        d["queue_position"] = next((i for i, j in enumerate(_queue) if j is job), 0) + 1
    return d


@app.post("/v1/videos")
def create_video(req: VideoRequest):
    prompt = (req.prompt or "").strip()
    if not prompt:
        raise HTTPException(400, "prompt is required")
    if req.quality not in QUALITY:
        raise HTTPException(400, f"quality must be one of {sorted(QUALITY)}")
    if req.aspect not in SIZES:
        raise HTTPException(400, f"aspect must be one of {sorted(SIZES)}")
    if req.image_b64:
        try:
            base64.b64decode(req.image_b64, validate=True)
        except Exception:
            raise HTTPException(400, "image_b64 is not valid base64")
    job = {"id": uuid.uuid4().hex[:12], "status": "queued", "stage": "queued", "step": 0,
           "prompt": prompt[:2000], "quality": req.quality, "aspect": req.aspect,
           "seconds": req.seconds, "seed": req.seed, "image_b64": req.image_b64,
           "created_at": time.time()}
    with _queue_cv:
        _jobs[job["id"]] = job
        _queue.append(job)
        _queue_cv.notify()
    return _public(job)


@app.get("/v1/videos/{job_id}")
def get_video(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "unknown job")
    return _public(job)


@app.get("/v1/videos/{job_id}/content")
def get_video_content(job_id: str):
    job = _jobs.get(job_id)
    if not job or job["status"] != "done" or not job.get("file"):
        raise HTTPException(404, "video not ready")
    return FileResponse(job["file"], media_type="video/mp4")


@app.get("/v1/models")
def list_models():
    return {"data": [{"id": m, "object": "model", "owned_by": "local", "quality": q}
                     for q, (m, _, _) in QUALITY.items()]}


@app.get("/health")
def health():
    running = [j["id"] for j in _jobs.values() if j["status"] == "running"]
    return {"status": "ok", "running": running, "queued": len(_queue),
            "mem_available_gb": round(mem_avail_gb(), 1)}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True, help="Wan2.2-TI2V-5B diffusers folder (text encoder, VAE, scheduler)")
    p.add_argument("--base-transformer", default=None,
                   help="Transformer for quality=high (default: <base>/transformer_bf16, else <base>/transformer)")
    p.add_argument("--turbo-transformer", required=True, help="4-step Turbo transformer folder (quality=fast)")
    p.add_argument("--output-dir", default=os.path.expanduser("~/myai-videogen/outputs"))
    p.add_argument("--gpu-lock", default=f"/run/user/{os.getuid()}/myai-diffusion.lock")
    p.add_argument("--image-server-url", default="", help="diffusion_server.py base URL to unload before renders")
    p.add_argument("--min-free-gb", type=float, default=24.0, help="Refuse to start a job below this")
    p.add_argument("--floor-gb", type=float, default=6.0, help="Abort a running job below this")
    p.add_argument("--hard-floor-gb", type=float, default=3.0, help="Exit the process below this")
    p.add_argument("--port", type=int, default=8102)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--allowed-host", action="append", default=[])
    _args = p.parse_args()
    if not _args.base_transformer:
        bf16 = Path(_args.base) / "transformer_bf16"
        _args.base_transformer = str(bf16 if bf16.exists() else Path(_args.base) / "transformer")
    Path(_args.output_dir).mkdir(parents=True, exist_ok=True)

    hosts = [h for h in dict.fromkeys([_args.host, "127.0.0.1", "localhost", "::1", *_args.allowed_host]) if h]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    threading.Thread(target=_worker, daemon=True).start()
    logger.info("video server: base=%s turbo=%s hosts=%s", _args.base, _args.turbo_transformer, hosts)
    uvicorn.run(app, host=_args.host, port=_args.port)
