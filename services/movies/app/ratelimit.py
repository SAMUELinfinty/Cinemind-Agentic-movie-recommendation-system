"""Tiny in-memory sliding-window rate limiter (demo-grade, single process)."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Return 429 JSON once a client exceeds max_requests per window_s.

    /health is always exempt. `clock` is injectable for tests.
    """

    def __init__(self, app, max_requests: int = 300, window_s: float = 60.0, clock=None):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_s = window_s
        self._clock = clock or time.monotonic
        self._hits: dict[str, list[float]] = {}

    async def dispatch(self, request, call_next):
        if request.url.path == "/health":
            return await call_next(request)
        key = request.client.host if request.client else "unknown"
        now = self._clock()
        cutoff = now - self.window_s
        times = [t for t in self._hits.get(key, []) if t > cutoff]
        if len(times) >= self.max_requests:
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
        times.append(now)
        self._hits[key] = times
        return await call_next(request)
