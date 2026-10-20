from __future__ import annotations

import math
import re
import time
from collections.abc import Callable
from urllib.parse import urlparse

from starlette.requests import Request

from .errors import ApiError

MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
MAX_BODY_BYTES = 64 * 1024


def security_headers(hsts: bool) -> dict[str, str]:
    headers = {
        "Content-Security-Policy": (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'; "
            "connect-src 'self'"
        ),
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-origin",
    }
    if hsts:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return headers


def check_csrf(request: Request) -> None:
    """Custom header + Origin/Host match on mutations (SEC-003); SameSite=Strict is the third layer."""
    if request.method not in MUTATING:
        return
    if request.headers.get("x-requested-with") != "planner":
        raise ApiError(403, "csrf", "Missing required request header")
    origin = request.headers.get("origin")
    if origin is not None:
        try:
            host = urlparse(origin).netloc
        except ValueError:
            host = None
        if host != request.headers.get("host"):
            raise ApiError(403, "csrf", "Cross-origin request rejected")


def check_content_type(request: Request) -> None:
    if request.method not in MUTATING:
        return
    has_body = request.headers.get("content-length", "0") not in {"", "0"} or "transfer-encoding" in request.headers
    if has_body and not re.match(r"^application/json\s*(;|$)", request.headers.get("content-type", ""), re.I):
        raise ApiError(415, "unsupported_media_type", "Content-Type must be application/json")


def client_ip(request: Request, trust_proxy: bool) -> str:
    if trust_proxy:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """Fixed-window in-memory limiter. Single-instance only (TD-002)."""

    def __init__(self, limit: int, window_s: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.limit = limit
        self.window_s = window_s
        self._clock = clock
        self._buckets: dict[str, list[float]] = {}

    def hit(self, key: str) -> tuple[bool, int]:
        now = self._clock()
        if len(self._buckets) > 10000:
            self._buckets = {k: b for k, b in self._buckets.items() if b[1] > now}
        bucket = self._buckets.get(key)
        if bucket is None or bucket[1] <= now:
            bucket = [0, now + self.window_s]
            self._buckets[key] = bucket
        bucket[0] += 1
        if bucket[0] > self.limit:
            return False, max(1, math.ceil(bucket[1] - now))
        return True, 0


def enforce(limiter: RateLimiter, key: str, message: str = "Too many requests") -> None:
    allowed, retry_after = limiter.hit(key)
    if not allowed:
        raise ApiError(429, "rate_limited", message, headers={"Retry-After": str(retry_after)})
