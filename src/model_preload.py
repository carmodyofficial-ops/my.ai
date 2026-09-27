"""Keep the active local chat model resident in ollama.

A cold ollama load reads the entire GGUF off disk before the server will answer
anything. On this box the model store lives on a USB spinning disk (~120 MB/s),
so a 93 GB model needs roughly 13 minutes to become ready. Every chat path gives
up long before that (LLMConfig.STREAM_TIMEOUT = 300s, DEFAULT_TIMEOUT = 120s,
AI_CHAT_TIMEOUT = 120s), and ollama *discards* a partial load the moment the
client disconnects:

    WARN  client connection closed before llama-server finished loading,
          aborting load
    INFO  Load failed ... error="timed out waiting for llama-server to start:
          context canceled"

So the load could never finish, every request came back 499, and chat produced
no tokens at all — the failure was a livelock, not a broken model.

The keepalive loop's ``/models`` ping does not fix this: it only proves the HTTP
server is up and never causes a model to load. This module issues a real
empty-prompt ``/api/generate`` with a long timeout, off the request path, so the
cold load runs to completion in the background exactly once and ``keep_alive``
then holds the model resident for subsequent chats.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Dict, Set
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

# How long to let a background load run. A cold 93 GB model off the USB HDD is
# ~13 min; leave generous headroom but stay under ollama's OLLAMA_LOAD_TIMEOUT.
PRELOAD_TIMEOUT = float(os.getenv("MYAI_PRELOAD_TIMEOUT", "1800") or "1800")

# Passed through to ollama so the model stays resident once loaded. The systemd
# unit already sets OLLAMA_KEEP_ALIVE=8h; sending it explicitly means a preload
# still pins the model if that env is ever dropped.
PRELOAD_KEEP_ALIVE = os.getenv("MYAI_PRELOAD_KEEP_ALIVE", "8h") or "8h"

# Disable with MYAI_PRELOAD=0 (e.g. on a box where loads must stay manual).
PRELOAD_ENABLED = (os.getenv("MYAI_PRELOAD", "1") or "1").strip().lower() not in {"0", "false", "no"}

# Models we never preload: embedding/reranker models are tiny and the RAG path
# loads them on demand anyway. Preloading one would be actively harmful, since
# it would consume a slot the chat model needs.
#
# Related, and the reason chat stayed broken even after a model finished
# loading: ollama ran with OLLAMA_MAX_LOADED_MODELS=1, so the 45 MB RAG embedder
# evicted the 64 GB chat model on the very next message ("loaded runners
# count=1"), forcing a fresh ~13 min load that then timed out. The drop-in now
# allows 2 resident models so the embedder and the chat model coexist.
_SKIP_SUBSTRINGS = ("embed", "minilm", "rerank")

# Endpoint root -> model currently being loaded by us. Guards against the 60s
# keepalive loop stacking a second load on top of an in-flight one, which would
# disconnect the first client and abort the very load we are waiting on.
_inflight: Dict[str, str] = {}
_inflight_lock = asyncio.Lock()

# Strong refs to the background load tasks. asyncio only keeps weak references
# to running tasks, so without this a preload can be garbage-collected
# mid-load — which disconnects the client and makes ollama abort the load,
# reproducing the exact bug this module exists to fix.
_tasks: Set[asyncio.Task] = set()


def _ollama_root(endpoint_url: str) -> str:
    """Return the server root for an endpoint URL, or "" if it isn't usable.

    Session rows store a full chat URL (".../v1/chat/completions") while
    ModelEndpoint rows store ".../v1"; both reduce to the same root, which is
    what ollama's native /api/* routes hang off.
    """
    if not endpoint_url:
        return ""
    parts = urlsplit(endpoint_url.strip())
    if not parts.scheme or not parts.netloc:
        return ""
    return f"{parts.scheme}://{parts.netloc}"


def _is_preloadable(model: str) -> bool:
    if not model:
        return False
    low = model.lower()
    return not any(s in low for s in _SKIP_SUBSTRINGS)


async def _loaded_models(client: httpx.AsyncClient, root: str) -> Set[str] | None:
    """Names currently resident in ollama, or None if this isn't an ollama server.

    The None case matters: a vLLM/llama.cpp endpoint has no /api/ps and no
    /api/generate either, so preloading it would just 404 once per keepalive
    tick. Those servers pin their model at process start and have no
    cold-load-on-request problem, so there is nothing to preload anyway.
    """
    try:
        r = await client.get(f"{root}/api/ps", timeout=5.0)
        if r.status_code != 200:
            return None
        return {m.get("name") or m.get("model") or "" for m in (r.json() or {}).get("models", [])}
    except Exception:
        return None


async def _preload_one(root: str, model: str) -> None:
    """Load ``model`` on ``root`` and wait for it, holding the connection open.

    Holding the connection open is the whole point: ollama cancels the load if
    the requesting client goes away, so a fire-and-forget request with a short
    timeout is worse than doing nothing.
    """
    async with _inflight_lock:
        if root in _inflight:
            return
        _inflight[root] = model
    try:
        logger.info("[preload] loading %s on %s (may take minutes on a cold store)", model, root)
        loop = asyncio.get_running_loop()
        started = loop.time()
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=PRELOAD_TIMEOUT,
                                                           write=30.0, pool=10.0)) as client:
            # Empty prompt = load only, no generation.
            r = await client.post(
                f"{root}/api/generate",
                json={"model": model, "prompt": "", "keep_alive": PRELOAD_KEEP_ALIVE},
            )
        if r.status_code == 200:
            logger.info("[preload] %s resident after %.0fs", model, loop.time() - started)
        else:
            logger.warning("[preload] %s failed: HTTP %s", model, r.status_code)
    except Exception as e:
        logger.warning("[preload] %s failed after timeout/error: %s: %s", model, type(e).__name__, e)
    finally:
        async with _inflight_lock:
            _inflight.pop(root, None)


def _recent_session_models() -> Dict[str, str]:
    """Most recently used chat model per endpoint root, newest session first.

    The model a user will actually hit next is the one their newest session is
    pointed at, so that is what is worth holding in memory.
    """
    targets: Dict[str, str] = {}
    try:
        from core.database import SessionLocal, Session as DbSession
    except Exception as e:  # pragma: no cover - import shape varies by entrypoint
        logger.debug("[preload] no DB access: %s", e)
        return targets
    db = SessionLocal()
    try:
        rows = (
            db.query(DbSession.model, DbSession.endpoint_url)
            .order_by(DbSession.updated_at.desc())
            .limit(50)
            .all()
        )
    except Exception as e:
        logger.debug("[preload] session query failed: %s", e)
        return targets
    finally:
        db.close()
    for model, endpoint_url in rows:
        root = _ollama_root(endpoint_url or "")
        if root and root not in targets and _is_preloadable(model or ""):
            targets[root] = model
    return targets


async def preload_active_models() -> None:
    """Ensure each local endpoint's most-recent chat model is resident.

    Safe to call repeatedly (the keepalive loop does): already-resident models
    and in-flight loads are skipped, so a steady state costs one /api/ps per
    endpoint.
    """
    if not PRELOAD_ENABLED:
        return
    targets = await asyncio.to_thread(_recent_session_models)
    if not targets:
        return
    async with httpx.AsyncClient() as client:
        for root, model in targets.items():
            async with _inflight_lock:
                if root in _inflight:
                    continue
            resident = await _loaded_models(client, root)
            if resident is None:
                continue  # not an ollama server — nothing to preload
            if model in resident:
                continue
            # Don't await: a cold load is minutes long and must not stall the
            # keepalive loop or app startup.
            task = asyncio.create_task(_preload_one(root, model))
            _tasks.add(task)
            task.add_done_callback(_tasks.discard)
