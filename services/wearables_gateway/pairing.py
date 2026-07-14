"""Device enrollment for the wearables gateway.

Two-step flow (an upgrade over companion/'s token-in-QR):

1. A logged-in admin POSTs /api/wearables/v1/pairings → a ONE-TIME pairing
   code (`wpair_…`) with a short TTL. Only its sha256 is kept in memory.
2. The phone POSTs the code to /api/wearables/v1/pair (auth-exempt,
   rate-limited) and receives a revocable device credential — a standard
   `ody_` ApiToken row scoped to "wearables", indistinguishable to the auth
   middleware from any other API token and revocable in Settings → API tokens
   or via DELETE /api/wearables/v1/devices/{id}.

The raw pairing code and the raw device token are each shown exactly once and
never persisted in clear. Replay resistance: codes are single-use (consumed
atomically under a lock) and expire after PAIRING_TTL_SECONDS.
"""

from __future__ import annotations

import hashlib
import secrets
import threading
import time
import uuid

PAIRING_TTL_SECONDS = 300
DEVICE_SCOPE = "wearables"
DEVICE_NAME_PREFIX = "wearable:"
_MAX_DEVICE_NAME = 60
_MAX_PENDING_CODES = 20  # an admin can't flood memory with unconsumed codes

# LAN-discovery enrollment (the "auto-discover + approve" flow):
ENROLL_TTL_SECONDS = 300
_MAX_PENDING_ENROLLMENTS = 30      # total pending approval requests
_MAX_PENDING_ENROLLMENTS_PER_IP = 3  # one phone shouldn't flood the approval UI


def _digest(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def sanitize_device_name(name: str | None) -> str:
    """Printable, length-capped device label; never trusted for anything but
    display in the token list."""
    cleaned = "".join(
        ch for ch in (name or "").strip() if ch.isprintable() and ch not in "<>\"'"
    )
    return cleaned[:_MAX_DEVICE_NAME] or "glasses-companion"


class PairingStore:
    """In-memory one-time pairing codes: sha256(code) → (owner, expires_at).

    In-memory is deliberate — a restart voids unconsumed codes, which is the
    safe failure mode for an enrollment secret.
    """

    def __init__(self, ttl_seconds: int = PAIRING_TTL_SECONDS):
        self.ttl = ttl_seconds
        self._codes: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    def mint(self, owner: str) -> str:
        """Create a pairing code for `owner`. Returns the raw code (show once)."""
        code = "wpair_" + secrets.token_urlsafe(24)
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            if len(self._codes) >= _MAX_PENDING_CODES:
                # Drop the oldest pending code rather than grow unboundedly.
                oldest = min(self._codes, key=lambda k: self._codes[k][1])
                del self._codes[oldest]
            self._codes[_digest(code)] = (owner, now + self.ttl)
        return code

    def consume(self, code: str) -> str | None:
        """Atomically redeem a code. Returns the owning username, or None if
        the code is unknown, already used, or expired."""
        if not isinstance(code, str) or not code.startswith("wpair_"):
            return None
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            entry = self._codes.pop(_digest(code), None)
        if entry is None:
            return None
        owner, expires_at = entry
        if now > expires_at:
            return None
        return owner

    def pending_count(self) -> int:
        with self._lock:
            self._prune(time.monotonic())
            return len(self._codes)

    def _prune(self, now: float) -> None:
        expired = [k for k, (_, exp) in self._codes.items() if now > exp]
        for k in expired:
            del self._codes[k]


class EnrollmentStore:
    """Pending LAN-discovery enrollments awaiting admin approval.

    The app discovers the host on the LAN, POSTs an enrollment request, and
    shows a short verify code. The admin sees the same code on the host and
    approves — so a rogue device on the LAN can't self-enroll, and the code
    confirms the admin is approving THIS device (like Bluetooth pairing).

    Three identifiers keep the trust boundaries clean:
      - request_id: high-entropy secret the app holds; the ONLY way to poll for
        the minted token. Never shown to the admin.
      - approval_id: short public handle the admin approves/denies by. Never
        lets you read the token.
      - verify_code: 4 digits shown to BOTH sides for human confirmation.
    In-memory + short TTL, same safe-failure posture as PairingStore.
    """

    def __init__(self, ttl_seconds: int = ENROLL_TTL_SECONDS):
        self.ttl = ttl_seconds
        # request_id -> dict(approval_id, verify_code, device_name, ip,
        #                    expires_at, status, token, token_id, owner)
        self._reqs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def request(self, device_name: str | None, ip: str) -> dict:
        """Create a pending enrollment. Returns the app-facing fields
        (request_id secret + verify_code + expires_in)."""
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            if sum(1 for r in self._reqs.values() if r["ip"] == ip) >= _MAX_PENDING_ENROLLMENTS_PER_IP:
                return {}  # caller maps to 429
            if len(self._reqs) >= _MAX_PENDING_ENROLLMENTS:
                oldest = min(self._reqs, key=lambda k: self._reqs[k]["expires_at"])
                self._drop(oldest)
            request_id = secrets.token_urlsafe(24)
            approval_id = secrets.token_hex(4)
            verify_code = f"{secrets.randbelow(10000):04d}"
            self._reqs[request_id] = {
                "approval_id": approval_id,
                "verify_code": verify_code,
                "device_name": sanitize_device_name(device_name),
                "ip": ip,
                "created_at": now,
                "expires_at": now + self.ttl,
                "status": "pending",
                "token": None,
                "token_id": None,
                "owner": None,
            }
        return {"request_id": request_id, "verify_code": verify_code,
                "expires_in": self.ttl}

    def list_pending(self) -> list[dict]:
        """Admin-facing view: never exposes request_id (the app's secret) or
        the token."""
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            return [
                {"approval_id": r["approval_id"], "verify_code": r["verify_code"],
                 "device_name": r["device_name"], "ip": r["ip"],
                 "age_seconds": int(now - r["created_at"])}
                for r in self._reqs.values() if r["status"] == "pending"
            ]

    def approve(self, approval_id: str, owner: str, invalidate=None) -> dict | None:
        """Admin approves by approval_id: mint the device token and attach it to
        the pending request for the app to poll. Returns a small summary, or
        None if the approval_id is unknown/expired/not pending."""
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            entry = next((r for r in self._reqs.values()
                          if r["approval_id"] == approval_id and r["status"] == "pending"), None)
            if entry is None:
                return None
            device_name = entry["device_name"]
        # Mint outside the lock (DB + bcrypt); a concurrent duplicate approve is
        # prevented by flipping status under the lock immediately after.
        token_id, raw_token = mint_device_token(owner, device_name, invalidate=invalidate)
        with self._lock:
            entry = next((r for r in self._reqs.values()
                          if r["approval_id"] == approval_id), None)
            if entry is None or entry["status"] != "pending":
                # Raced with expiry/deny/another approve — the token we minted is
                # orphaned; revoke it so we don't leave a live credential nobody polls for.
                revoke_device(token_id, invalidate=invalidate)
                return None
            entry.update(status="approved", token=raw_token, token_id=token_id, owner=owner)
        return {"approval_id": approval_id, "token_id": token_id, "device_name": device_name}

    def deny(self, approval_id: str) -> bool:
        with self._lock:
            self._prune(time.monotonic())
            for rid, r in list(self._reqs.items()):
                if r["approval_id"] == approval_id and r["status"] == "pending":
                    del self._reqs[rid]
                    return True
        return False

    def poll(self, request_id: str) -> dict:
        """App polls by its secret request_id. On approval the token is
        delivered EXACTLY ONCE (the request is then removed). Statuses:
        pending | approved | denied_or_expired."""
        if not isinstance(request_id, str) or not request_id:
            return {"status": "denied_or_expired"}
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            entry = self._reqs.get(request_id)
            if entry is None:
                return {"status": "denied_or_expired"}
            if entry["status"] != "approved":
                return {"status": "pending"}
            # Single delivery: hand back the token and drop the request.
            out = {"status": "approved", "token": entry["token"],
                   "token_id": entry["token_id"], "owner": entry["owner"],
                   "scope": DEVICE_SCOPE, "api_base": "/api/wearables/v1"}
            del self._reqs[request_id]
        return out

    def pending_count(self) -> int:
        with self._lock:
            self._prune(time.monotonic())
            return len(self._reqs)

    def _prune(self, now: float) -> None:
        for k in [k for k, r in self._reqs.items() if now > r["expires_at"]]:
            self._drop(k)

    def _drop(self, request_id: str) -> None:
        """Remove a pending/approved request. If it was approved but never polled,
        revoke the orphaned device token so we don't leave a live-but-unclaimed
        credential in the DB (mirrors the orphan-revoke in approve()). The raw
        token was never delivered, so no auth cache needs invalidation."""
        entry = self._reqs.pop(request_id, None)
        if entry and entry.get("status") == "approved" and entry.get("token_id"):
            try:
                revoke_device(entry["token_id"])
            except Exception:
                pass


def mint_device_token(owner: str, device_name: str | None = None,
                      invalidate=None) -> tuple[str, str]:
    """Create a wearables-scoped ApiToken for a paired device.

    Returns (token_id, raw_token); the raw token is returned ONCE — only its
    bcrypt hash + 8-char prefix are persisted (same contract as
    companion/pairing.mint_token and routes/api_token_routes). `invalidate`
    is app.state.invalidate_token_cache so the credential works on the very
    next request without a restart.
    """
    import bcrypt

    from core.database import get_db_session, ApiToken

    raw_token = "ody_" + secrets.token_urlsafe(32)
    token_hash = bcrypt.hashpw(raw_token.encode(), bcrypt.gensalt()).decode()
    token_id = str(uuid.uuid4())[:8]

    with get_db_session() as db:
        db.add(ApiToken(
            id=token_id,
            owner=owner,
            name=DEVICE_NAME_PREFIX + sanitize_device_name(device_name),
            token_hash=token_hash,
            token_prefix=raw_token[:8],
            scopes=DEVICE_SCOPE,
            is_active=True,
        ))
    if callable(invalidate):
        invalidate()
    return token_id, raw_token


def list_devices() -> list[dict]:
    """Wearable device credentials (active and revoked), no secret material."""
    from core.database import get_db_session, ApiToken

    out: list[dict] = []
    with get_db_session() as db:
        rows = db.query(ApiToken).all()
        for r in rows:
            scopes = [s.strip() for s in (r.scopes or "").split(",") if s.strip()]
            if DEVICE_SCOPE not in scopes:
                continue
            out.append({
                "token_id": r.id,
                "owner": r.owner,
                "name": r.name,
                "active": bool(r.is_active),
                "created_at": str(getattr(r, "created_at", "") or ""),
                "last_used_at": str(getattr(r, "last_used_at", "") or ""),
            })
    return out


def revoke_device(token_id: str, invalidate=None) -> bool:
    """Deactivate a wearable device credential. Idempotent; True if the row
    existed and is a wearables credential."""
    from core.database import get_db_session, ApiToken

    with get_db_session() as db:
        row = db.query(ApiToken).filter(ApiToken.id == token_id).first()
        if row is None:
            return False
        scopes = [s.strip() for s in (row.scopes or "").split(",") if s.strip()]
        if DEVICE_SCOPE not in scopes:
            return False
        row.is_active = False
    if callable(invalidate):
        invalidate()
    return True
