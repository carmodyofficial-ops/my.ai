# src/rate_limiter.py
"""Generic in-memory rate limiter — sliding window, keyed by IP."""

import threading
import time
from typing import Dict, List


class RateLimiter:
    """Sliding-window rate limiter.

    Usage:
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        if not limiter.check(ip):
            raise HTTPException(429, "Too many requests")
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self._log: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.monotonic()
        self._cleanup_interval = max(window_seconds * 2, 120)

    def check(self, key: str) -> bool:
        """Return True if the request is allowed, False if rate-limited."""
        now = time.monotonic()
        with self._lock:
            self._maybe_cleanup(now)
            timestamps = self._log.get(key, [])
            cutoff = now - self.window
            timestamps = [t for t in timestamps if t > cutoff]
            if len(timestamps) >= self.max_requests:
                self._log[key] = timestamps
                return False
            timestamps.append(now)
            self._log[key] = timestamps
            return True

    def _maybe_cleanup(self, now: float) -> None:
        """Periodically purge stale entries."""
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        cutoff = now - self.window
        stale = [k for k, v in self._log.items() if not v or v[-1] <= cutoff]
        for k in stale:
            del self._log[k]


class AccountLockout:
    """Per-account failed-login lockout, keyed by username.

    Counts failed attempts within a sliding window; after ``max_failures`` the
    account is locked for ``lockout_seconds`` and every attempt is refused until
    the lock expires. A successful login clears the counter.

    This defends credential brute force where an IP rate limiter cannot: behind
    Docker NAT (or any shared egress) every client presents the same source IP,
    so IP keying collapses to a single global bucket. Keying on the username
    restores per-account protection. Trade-off: an attacker who knows a username
    can force a temporary lock on it (a nuisance DoS); the moderate threshold and
    auto-expiring window keep that bounded, and a real user simply waits it out.
    """

    def __init__(
        self,
        max_failures: int = 8,
        lockout_seconds: int = 900,
        window_seconds: int = 900,
    ):
        self.max_failures = max_failures
        self.lockout_seconds = lockout_seconds
        self.window = window_seconds
        self._fails: Dict[str, List[float]] = {}
        self._locked_until: Dict[str, float] = {}
        self._lock = threading.Lock()

    def locked_for(self, key: str) -> float:
        """Seconds remaining on an active lock for ``key`` (0.0 if not locked)."""
        now = time.monotonic()
        with self._lock:
            return max(0.0, self._locked_until.get(key, 0.0) - now)

    def record_failure(self, key: str) -> float:
        """Record a failed attempt. Returns the remaining lock duration if this
        attempt triggered (or fell within) a lock, else 0.0."""
        now = time.monotonic()
        with self._lock:
            until = self._locked_until.get(key, 0.0)
            if until > now:
                return until - now
            cutoff = now - self.window
            fails = [t for t in self._fails.get(key, []) if t > cutoff]
            fails.append(now)
            if len(fails) >= self.max_failures:
                self._locked_until[key] = now + self.lockout_seconds
                self._fails.pop(key, None)
                return float(self.lockout_seconds)
            self._fails[key] = fails
            return 0.0

    def record_success(self, key: str) -> None:
        """Clear all failure state for ``key`` after a successful login."""
        with self._lock:
            self._fails.pop(key, None)
            self._locked_until.pop(key, None)
