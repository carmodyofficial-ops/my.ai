#!/usr/bin/env python3
"""Background-job client for the generate_video tool.

Lives in src/ (not scripts/) because only src/ is bind-mounted into the
container. Launched detached by src/tool_execution._launch_generate_video via bg_jobs.
Submits a render to scripts/video_server.py, waits for it, saves the mp4 into
the generated-images store + gallery, and prints a result block. bg_monitor
feeds that output back to the agent, and lifts the link into a video bubble.

Usage: python3 src/video_client.py --spec /app/data/bg_jobs/video-<id>.json
"""
import argparse
import base64
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

POLL_S = 10
# A lost server job (restart) or a render stuck on one stage this long is a failure.
STAGE_STALL_S = 1800


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    spec_path = Path(ap.parse_args().spec)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    base = spec["server_url"].rstrip("/")

    body = {"prompt": spec["prompt"], "quality": spec["quality"], "aspect": spec["aspect"],
            "seconds": spec["seconds"]}
    if spec.get("image_path"):
        body["image_b64"] = base64.b64encode(Path(spec["image_path"]).read_bytes()).decode()

    with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
        try:
            r = client.post(f"{base}/v1/videos", json=body)
            r.raise_for_status()
        except Exception as e:
            print(f"Video generation failed: could not reach the video server at {base} ({e}).")
            return 1
        job = r.json()
        print(f"Submitted video job {job['id']} ({spec['quality']} quality).", flush=True)

        last_stage, stage_since, t0 = None, time.time(), time.time()
        while job["status"] not in ("done", "failed"):
            time.sleep(POLL_S)
            try:
                r = client.get(f"{base}/v1/videos/{job['id']}")
            except httpx.HTTPError:
                continue  # transient; the stall check below bounds this
            if r.status_code == 404:
                print("Video generation failed: the video server lost the job (it probably restarted).")
                return 1
            job = r.json()
            stage = job.get("stage")
            if stage != last_stage:
                print(f"[{time.time() - t0:5.0f}s] {stage}", flush=True)
                last_stage, stage_since = stage, time.time()
            elif time.time() - stage_since > STAGE_STALL_S:
                print(f"Video generation failed: stuck in '{stage}' for {STAGE_STALL_S // 60} minutes.")
                return 1

        if job["status"] == "failed":
            print(f"Video generation failed: {job.get('error') or 'unknown error'}")
            return 1

        r = client.get(f"{base}/v1/videos/{job['id']}/content", timeout=httpx.Timeout(300.0))
        r.raise_for_status()
        data = r.content

    from src.constants import GENERATED_IMAGES_DIR
    out_dir = Path(GENERATED_IMAGES_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Content-hash name: the /api/generated-image route only serves hex names.
    filename = f"{hashlib.sha256(data).hexdigest()[:16]}.mp4"
    (out_dir / filename).write_bytes(data)

    try:
        from src.database import SessionLocal, GalleryImage
        db = SessionLocal()
        try:
            db.add(GalleryImage(
                id=str(uuid.uuid4()), filename=filename, prompt=spec["prompt"],
                model=job.get("model"), size=job.get("size"), quality=spec["quality"],
                owner=spec.get("owner"),
                file_hash=hashlib.sha256(data).hexdigest(),
            ))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"(gallery save skipped: {e})")

    try:
        spec_path.unlink()
    except OSError:
        pass

    seconds = round((job.get("frames") or 0) / 24, 1)
    render_s = round((job.get("ended_at") or 0) - (job.get("started_at") or 0))
    # Keep this block's labels stable: bg_monitor parses "Direct link:" / "Generated video for:".
    print(f"Generated video for: {spec['prompt'][:200]}")
    print(f"Direct link: {spec.get('public_base', '')}/api/generated-image/{filename}")
    print(f"model: {job.get('model')}")
    print(f"size: {job.get('size')}, {seconds}s at 24 fps")
    print(f"render time: {render_s // 60}m {render_s % 60}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
