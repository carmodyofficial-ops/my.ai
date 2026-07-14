"""Field Mode over WhatsApp (Twilio) — receive a prompt, answer with read-only
tools, reply over WhatsApp. Off by default.

Design (matches the project's hard safety rules — see the d19/w2 turnovers):
- The home box NEVER accepts inbound internet traffic. We POLL Twilio's REST API
  (outbound HTTPS only) for inbound messages and POST replies the same way, so the
  app stays loopback-only; no public exposure, no listening port.
- Only allowlisted operator numbers are processed (deny-by-default).
- A shell/secret keyword deny-list blocks dangerous intents outright.
- The prompt is answered by the agent in a RESTRICTED mode: read-only tools only
  (web_search/web_fetch) — bash/python/shell/git and all file-write/read tools are
  hard-disabled, so WhatsApp can never drive execution or read the host filesystem.
- Replies are redacted (no secrets) and length-capped. Sending is gated behind an
  explicit env flag; with it off, answers are recorded locally (receive-only).

Enable: set in ~/.config/myai/whatsapp/whatsapp_provider.env
    MYAI_WHATSAPP_FIELD_MODE_ENABLED=true        # master switch for this bridge
    MYAI_WHATSAPP_PROVIDER_SEND_ENABLED=true      # actually send WhatsApp replies
plus TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_WHATSAPP_FROM and the operator
allowlist (MYAI_WHATSAPP_OPERATOR_ALLOWLIST or OPERATOR_ALLOWLIST).
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

STATE_DIR = Path(os.environ.get("DATA_DIR", "/app/data")) / "whatsapp_field_mode"


def _resolve_env_file() -> Path:
    """Locate the WhatsApp provider env file.

    The app runs in-container where the host's ~/.config path is absent, so we
    prefer a bind-mounted, container-readable location. Order:
      1. MYAI_WHATSAPP_ENV_FILE (explicit override)
      2. <DATA_DIR>/whatsapp_field_mode/provider.env  (bind-mounted; in-container)
      3. ~/.config/myai/whatsapp/whatsapp_provider.env (host / native runs)
    """
    override = os.environ.get("MYAI_WHATSAPP_ENV_FILE")
    candidates = [Path(override)] if override else []
    candidates.append(STATE_DIR / "provider.env")
    candidates.append(Path.home() / ".config/myai/whatsapp/whatsapp_provider.env")
    for c in candidates:
        try:
            if c.exists():
                return c
        except Exception:
            continue
    return candidates[-1]


ENV_FILE = _resolve_env_file()
SEEN_FILE = STATE_DIR / "seen_message_sids.json"
EVENTS_FILE = STATE_DIR / "events.jsonl"

POLL_INTERVAL_S = 15
MAX_ROUNDS = 6
REPLY_MAX_CHARS = 1400

# Read-only tools the WhatsApp agent may use. Deliberately excludes the filesystem
# read tools (read_file/grep/glob/ls) that are in PLAN_MODE_READONLY_TOOLS — reading
# host files over a messaging channel is an exfiltration risk. The agent still gets
# the operator's memory/notes via the system-prompt context it auto-injects.
WHATSAPP_READONLY_TOOLS = {"web_search", "web_fetch"}

# Hard-disabled regardless of anything else (belt-and-suspenders with relevant_tools).
WHATSAPP_DISABLED_TOOLS = {
    "bash", "python", "shell", "terminal", "git",
    "write_file", "edit_file", "read_file", "grep", "glob", "ls", "get_workspace",
    "manage_memory", "manage_notes", "create_document", "update_document",
    "edit_document", "manage_documents", "manage_skills", "manage_mcp", "app_api",
}

# Intent deny-list: shell/secret/exposure phrasing is refused, never answered.
_BLOCKED_RE = re.compile(
    r"\b(sudo|systemctl|docker|iptables|ufw|ssh|scp|rm\s+-rf|printenv|chmod|chown|"
    r"git\s+(push|commit|reset)|expose\s+(model|lan)|port\s*forward|restart|reboot|"
    r"shutdown|curl|wget|nc\s|netcat)\b", re.IGNORECASE)
_SECRET_READ_RE = re.compile(r"cat\s+.*(\.env|secret|token|key|password)", re.IGNORECASE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text(errors="replace").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _truthy(v: Optional[str]) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> dict[str, Any]:
    env_file = _resolve_env_file()
    env = _parse_env(env_file)
    allow = (env.get("MYAI_WHATSAPP_OPERATOR_ALLOWLIST")
             or env.get("OPERATOR_ALLOWLIST") or os.environ.get("MYAI_WHATSAPP_OPERATOR_ALLOWLIST") or "")
    allowlist = [x.strip() for x in allow.split(",") if x.strip()]
    return {
        "env_file": str(env_file),
        "env_file_found": env_file.exists(),
        "sid": env.get("TWILIO_ACCOUNT_SID") or os.environ.get("TWILIO_ACCOUNT_SID"),
        "token": env.get("TWILIO_AUTH_TOKEN") or os.environ.get("TWILIO_AUTH_TOKEN"),
        "from_number": env.get("TWILIO_WHATSAPP_FROM") or os.environ.get("TWILIO_WHATSAPP_FROM") or "",
        "model": (env.get("MYAI_WHATSAPP_MODEL") or os.environ.get("MYAI_WHATSAPP_MODEL") or "").strip(),
        "allowlist": allowlist,
        "enabled": _truthy(env.get("MYAI_WHATSAPP_FIELD_MODE_ENABLED")),
        "send_enabled": _truthy(env.get("MYAI_WHATSAPP_PROVIDER_SEND_ENABLED")),
    }


def is_configured(cfg: Optional[dict] = None) -> bool:
    cfg = cfg or load_config()
    return bool(cfg["sid"] and cfg["token"] and cfg["allowlist"])


def _redact(text: str) -> str:
    """Strip anything that looks like a secret and cap length for WhatsApp."""
    t = str(text or "")
    t = re.sub(r"\b(sk-[A-Za-z0-9]{8,}|AC[a-f0-9]{30,}|Bearer\s+[A-Za-z0-9._\-]+)\b",
               "[redacted]", t)
    t = re.sub(r"\b[A-Fa-f0-9]{40,}\b", "[redacted]", t)  # long hex tokens
    t = t.strip()
    if len(t) > REPLY_MAX_CHARS:
        t = t[:REPLY_MAX_CHARS].rstrip() + " …(truncated)"
    return t or "(no answer)"


def _is_blocked(text: str) -> bool:
    return bool(_BLOCKED_RE.search(text or "") or _SECRET_READ_RE.search(text or ""))


# ── Twilio REST (blocking; callers wrap in asyncio.to_thread) ──

def _twilio_auth(sid: str, token: str) -> str:
    return "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode()


def _twilio_get_inbound(sid: str, token: str) -> tuple[Optional[int], list[dict]]:
    url = (f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json?"
           + urllib.parse.urlencode({"PageSize": "50"}))
    req = urllib.request.Request(url, headers={"Authorization": _twilio_auth(sid, token)})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            data = json.loads(res.read().decode())
            return res.status, data.get("messages", [])
    except urllib.error.HTTPError as e:
        logger.warning("WhatsApp poll HTTP %s: %s", e.code, e.read().decode(errors="replace")[:200])
        return e.code, []
    except Exception as e:
        logger.warning("WhatsApp poll failed: %s", e)
        return None, []


def _twilio_send(sid: str, token: str, from_: str, to: str, body: str) -> tuple[Optional[int], str]:
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    form = urllib.parse.urlencode({"From": from_, "To": to, "Body": body}).encode()
    req = urllib.request.Request(url, data=form, headers={
        "Authorization": _twilio_auth(sid, token),
        "Content-Type": "application/x-www-form-urlencoded",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.status, json.loads(res.read().decode()).get("sid", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:200]
    except Exception as e:
        return None, str(e)[:200]


# ── state ──

def _load_seen() -> set[str]:
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text()).get("seen_sids", []))
        except Exception:
            return set()
    return set()


def _save_seen(seen: set[str]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps({"updated_at": _now(), "seen_sids": sorted(seen)}, indent=2) + "\n")


def _record(event: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with EVENTS_FILE.open("a") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")


# ── agent ──

async def _answer_prompt(prompt: str, cfg: Optional[dict] = None) -> str:
    """Run the agent in read-only mode and return a text answer."""
    from src.agent_loop import stream_agent_loop
    from src.endpoint_resolver import resolve_endpoint

    cfg = cfg or load_config()
    endpoint_url, model, headers = resolve_endpoint("default", owner="admin")
    # Let the operator pin a reliable Field-Mode model (MYAI_WHATSAPP_MODEL) served
    # on the default endpoint — the global default may be a heavy/unsuitable model.
    if cfg.get("model"):
        model = cfg["model"]
    if not (endpoint_url and model):
        return "Field Mode: no model endpoint configured."

    messages = [
        {"role": "system", "content": (
            "You are the operator's personal assistant answering over WhatsApp (Field Mode). "
            "Reply in plain text, concise enough for a phone (a few short sentences). You may use "
            "web_search/web_fetch to look things up. You cannot run commands or change anything — "
            "this is read-only. Never include secrets, tokens, file contents, or internal paths.")},
        {"role": "user", "content": str(prompt).strip()},
    ]
    full = ""
    try:
        async for chunk in stream_agent_loop(
            endpoint_url, model, messages,
            headers=headers or {}, owner="admin",
            relevant_tools=set(WHATSAPP_READONLY_TOOLS),
            # Hard cap — the deny-set alone let intent-widening add mutating
            # tools back for an admin owner (same root cause as wearables).
            tool_allowlist=set(WHATSAPP_READONLY_TOOLS),
            disabled_tools=set(WHATSAPP_DISABLED_TOOLS),
            max_rounds=MAX_ROUNDS,
        ):
            if not chunk.startswith("data: "):
                continue
            body = chunk[6:].strip()
            if not body or body == "[DONE]":
                continue
            try:
                d = json.loads(body)
            except (ValueError, TypeError):
                continue
            if isinstance(d, dict) and "delta" in d:
                delta = d.get("delta")
                if isinstance(delta, str) and not d.get("thinking"):
                    full += delta
    except Exception as e:
        logger.warning("WhatsApp agent run failed: %s", e)
        return "Field Mode: could not generate an answer right now."
    return full.strip() or "(no answer)"


# ── poll + process ──

async def process_once(cfg: Optional[dict] = None, *, prime: bool = False) -> dict:
    """One poll cycle. With prime=True, mark all current inbound as seen and answer
    nothing (used on first start so the backlog of old messages isn't replied to)."""
    cfg = cfg or load_config()
    if not is_configured(cfg):
        return {"ok": False, "reason": "not_configured"}

    status, messages = await asyncio.to_thread(_twilio_get_inbound, cfg["sid"], cfg["token"])
    if status != 200:
        return {"ok": False, "reason": f"poll_http_{status}"}

    seen = _load_seen()
    allowlist = cfg["allowlist"]
    processed = 0
    for msg in reversed(messages):  # oldest first
        if msg.get("direction") != "inbound":
            continue
        sid = msg.get("sid") or ""
        raw_from = msg.get("from") or ""
        phone = raw_from.replace("whatsapp:", "")
        if raw_from not in allowlist and phone not in allowlist:
            continue
        if sid in seen:
            continue
        seen.add(sid)
        if prime:
            continue  # backlog: mark seen, do not answer

        body = (msg.get("body") or "").strip()
        last4 = re.sub(r"\D", "", phone)[-4:]
        if not body:
            continue
        if _is_blocked(body):
            answer = "That request is blocked by Field Mode policy (no shell, secrets, or system changes over WhatsApp)."
            category = "blocked_policy"
        else:
            answer = _redact(await _answer_prompt(body, cfg))
            category = "answered"

        reply_sent = False
        send_result = None
        if cfg["send_enabled"] and cfg["from_number"]:
            code, info = await asyncio.to_thread(
                _twilio_send, cfg["sid"], cfg["token"], cfg["from_number"], raw_from, answer)
            reply_sent = code in (200, 201)
            send_result = code if reply_sent else f"{code}:{info}"
        _record({
            "at": _now(), "message_sid": sid, "from_last4": last4,
            "category": category, "prompt": body[:500], "answer": answer[:1000],
            "reply_sent": reply_sent, "send_result": send_result,
            "send_enabled": cfg["send_enabled"],
        })
        processed += 1

    _save_seen(seen)
    return {"ok": True, "processed": processed, "primed": prime}


async def _loop() -> None:
    cfg = load_config()
    logger.info("WhatsApp Field Mode loop starting (send_enabled=%s, operators=%d)",
                cfg["send_enabled"], len(cfg["allowlist"]))
    # Prime once so the existing backlog of inbound messages is not answered.
    if not SEEN_FILE.exists():
        try:
            await process_once(cfg, prime=True)
        except Exception as e:
            logger.warning("WhatsApp Field Mode prime failed: %s", e)
    while True:
        try:
            await process_once()
        except Exception as e:
            logger.warning("WhatsApp Field Mode cycle error: %s", e)
        await asyncio.sleep(POLL_INTERVAL_S)


_task: Optional[asyncio.Task] = None


def start_whatsapp_field_mode() -> Optional[asyncio.Task]:
    """Start the background poller IFF enabled and configured. Returns the task or None."""
    global _task
    cfg = load_config()
    if not cfg["enabled"]:
        logger.info("WhatsApp Field Mode disabled (MYAI_WHATSAPP_FIELD_MODE_ENABLED not set).")
        return None
    if not is_configured(cfg):
        logger.warning("WhatsApp Field Mode enabled but not configured (missing creds/allowlist).")
        return None
    if _task and not _task.done():
        return _task
    _task = asyncio.create_task(_loop())
    return _task


def status() -> dict:
    cfg = load_config()
    return {
        "enabled": cfg["enabled"],
        "configured": is_configured(cfg),
        "send_enabled": cfg["send_enabled"],
        "operator_count": len(cfg["allowlist"]),
        "from_number_set": bool(cfg["from_number"]),
        "model": cfg.get("model") or "(default)",
        "env_file": cfg.get("env_file"),
        "env_file_found": cfg.get("env_file_found"),
        "running": bool(_task and not _task.done()),
        "readonly_tools": sorted(WHATSAPP_READONLY_TOOLS),
        "events_log": str(EVENTS_FILE),
    }
