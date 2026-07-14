"""Capability discovery for the wearables gateway.

The client never guesses: /capabilities reports what actually works right now
(STT, TTS, LLM, vision, tools) so the app can grey out Look-and-Ask, fall back
from voice to text, etc. Availability is computed from the live services —
no hardcoded optimism.
"""

from __future__ import annotations

import logging
import os
import threading
import time

logger = logging.getLogger(__name__)

# Deterministic preference when auto-detecting a local vision model. Both are
# installed and report the "vision" capability from Ollama as of 2026-07-12;
# override with the `wearables_vision_model` setting.
VISION_MODEL_PREFERENCE = ["qwen3.6:27b", "mistral-small3.2:24b"]
_VISION_CACHE_TTL = 600
# A *negative* result (Ollama down/slow mid-detection) must not be cached for
# the full 10 minutes — that would keep reporting VISION_MODEL_NOT_CONFIGURED
# long after Ollama recovers. Re-probe negatives quickly.
_VISION_NEG_CACHE_TTL = 15

_vision_cache: dict = {"expires": 0.0, "result": None}
_vision_lock = threading.Lock()


def _ollama_root() -> str:
    base = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    root = base.rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3].rstrip("/")
    return root


def resolve_vision_model(force_refresh: bool = False) -> dict | None:
    """The local vision model to use for Look-and-Ask, or None.

    Order: explicit `wearables_vision_model` setting, else auto-detect a
    vision-capable installed Ollama model (capability reported by Ollama
    itself via /api/show — we do not invent multimodal support). Result is
    {"model": name, "chat_url": openai-compat url} and is cached 10 minutes.
    """
    from src import settings

    root = _ollama_root()
    chat_url = root + "/v1/chat/completions"

    configured = str(settings.get_setting("wearables_vision_model", "") or "").strip()
    if configured:
        return {"model": configured, "chat_url": chat_url, "source": "setting"}

    now = time.monotonic()
    with _vision_lock:
        if not force_refresh and now < _vision_cache["expires"]:
            return _vision_cache["result"]

    result = _detect_vision_model(root, chat_url)
    with _vision_lock:
        _vision_cache["result"] = result
        _vision_cache["expires"] = now + (
            _VISION_CACHE_TTL if result is not None else _VISION_NEG_CACHE_TTL)
    return result


def _detect_vision_model(root: str, chat_url: str) -> dict | None:
    try:
        import httpx

        with httpx.Client(timeout=5.0) as client:
            tags = client.get(root + "/api/tags").json()
            installed = [m.get("name", "") for m in tags.get("models", []) if m.get("name")]

            def is_vision(name: str) -> bool:
                try:
                    show = client.post(root + "/api/show", json={"model": name}).json()
                    return "vision" in (show.get("capabilities") or [])
                except Exception:
                    return False

            ordered = [m for m in VISION_MODEL_PREFERENCE if m in installed]
            ordered += [m for m in installed if m not in ordered]
            probes = 0
            for name in ordered:
                if probes >= 8:
                    break
                probes += 1
                if is_vision(name):
                    return {"model": name, "chat_url": chat_url, "source": "auto"}
    except Exception as e:
        logger.warning(f"Vision model detection failed: {e}")
    return None


async def warm_vision_model(keep_alive: str = "20m") -> dict:
    """Preload the Look-and-Ask vision model into VRAM and pin it warm.

    Uses Ollama's native ``/api/generate`` with an empty prompt — the documented
    "load a model" call: it returns as soon as the model is resident (done_reason
    "load") without generating, and ``keep_alive`` sets how long it stays loaded.
    The app calls this when Look-and-Ask becomes available so the FIRST look
    doesn't pay the cold-load; actual look requests then refresh the same window.
    Best-effort — a failure just means the next look loads on demand as before.
    ``keep_alive="0"`` is honored by Ollama as "unload immediately" (opt-out).
    """
    import asyncio

    if (keep_alive or "").strip() == "0":
        # Opt-out: "0" means "don't keep it warm". Skip entirely — otherwise the
        # /api/generate call below would LOAD the model and then immediately unload
        # it (keep_alive:0), paying a pointless cold-load.
        return {"warmed": False, "reason": "disabled"}
    vision = await asyncio.to_thread(resolve_vision_model)
    if not vision:
        return {"warmed": False, "reason": "VISION_MODEL_NOT_CONFIGURED"}
    root = _ollama_root()
    try:
        import httpx

        # A generous timeout: a cold 24-27B load can take a while, and we want the
        # request to stay in flight until Ollama finishes loading (a client
        # disconnect can abort the load).
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                root + "/api/generate",
                json={"model": vision["model"], "prompt": "",
                      "stream": False, "keep_alive": keep_alive},
            )
            r.raise_for_status()
        return {"warmed": True, "model": vision["model"], "keep_alive": keep_alive}
    except Exception as e:
        logger.warning(f"Vision warm failed: {e}")
        return {"warmed": False, "model": vision["model"], "reason": "warm_failed"}


def build_capabilities(stt_service, tts_service, owner: str | None) -> dict:
    """Honest, current component availability for one caller."""
    from src import settings
    from src.endpoint_resolver import resolve_endpoint

    llm_url, llm_model, _ = (None, None, None)
    try:
        llm_url, llm_model, _ = resolve_endpoint("default", owner=owner)
        # Report the model the glasses /respond path ACTUALLY uses, not the raw
        # default-endpoint model. /respond pins local chat to the fast "simple"
        # tier (auto_model_simple, e.g. gpt-oss:20b); without mirroring that here
        # the app displayed the 120b default while inference ran the 20b.
        if llm_url:
            from src.model_router import _is_local
            if _is_local(llm_url):
                fast = settings.get_setting("auto_model_simple", "gpt-oss:20b")
                fast = (str(fast).strip() if fast is not None else "")
                if fast:
                    llm_model = fast
    except Exception as e:
        logger.warning(f"LLM endpoint resolution failed: {e}")

    stt_provider = str(settings.get_setting("stt_provider", "disabled") or "disabled")
    tts_provider = str(settings.get_setting("tts_provider", "disabled") or "disabled")
    try:
        stt_available = bool(stt_service is not None and stt_service.available)
    except Exception:
        stt_available = False
    try:
        tts_available = bool(tts_service is not None and tts_service.available)
    except Exception:
        tts_available = False

    vision = None
    try:
        vision = resolve_vision_model()
    except Exception as e:
        logger.warning(f"Vision capability check failed: {e}")

    from src.upload_limits import STT_MAX_AUDIO_BYTES, WEARABLES_IMAGE_MAX_BYTES
    from routes.wearables_routes import MAX_TEXT_CHARS, WEARABLES_TOOLS

    return {
        "service": "wearables_gateway",
        "api_version": 1,
        "owner": owner,
        "stt": {"available": stt_available, "provider": stt_provider},
        "tts": {"available": tts_available, "provider": tts_provider},
        "llm": {
            "available": bool(llm_url and llm_model),
            "model": llm_model or None,
            "streaming": True,
        },
        "vision": {
            "available": vision is not None,
            "model": (vision or {}).get("model"),
            "state": "ok" if vision else "VISION_MODEL_NOT_CONFIGURED",
        },
        "memory": {"available": False, "reason": "not wired in v1 (privacy default)"},
        "tools": {"available": sorted(WEARABLES_TOOLS)},
        "limits": {
            "audio_max_bytes": STT_MAX_AUDIO_BYTES,
            "image_max_bytes": WEARABLES_IMAGE_MAX_BYTES,
            "text_max_chars": MAX_TEXT_CHARS,
        },
    }
