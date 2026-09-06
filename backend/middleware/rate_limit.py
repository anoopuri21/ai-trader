"""
Simple In-Memory Rate Limiter (no Redis required)

Per-IP sliding window using TTLCache + deque.
Limits:
  - Global: 60 req/min per IP
  - Strict endpoints: 10/min (analyze) , 5/min (auth-sensitive)

Security: Prevents brute-force & Yahoo Finance DoS.
         Returns 429 with Retry-After.

Usage:
  from middleware.rate_limit import limiter, rate_limit

  @router.get("/analyze/{symbol}")
  @rate_limit("strict")  # or "global"
"""

import time
import logging
from collections import deque, defaultdict
from typing import Dict, Deque

from fastapi import Request, HTTPException
from functools import wraps

logger = logging.getLogger(__name__)

# ─── Config ─────────────────────────────────────────────────────────
GLOBAL_LIMIT = 60  # req per 60s
GLOBAL_WINDOW = 60

STRICT_LIMIT = 10  # for analyze/backtest
STRICT_WINDOW = 60

AUTH_LIMIT = 5
AUTH_WINDOW = 60

# In-memory store: { ip: deque[timestamps] }
_store: Dict[str, Deque[float]] = defaultdict(deque)
_strict_store: Dict[str, Deque[float]] = defaultdict(deque)
_auth_store: Dict[str, Deque[float]] = defaultdict(deque)


def _is_limited(store: Dict[str, Deque[float]], key: str, limit: int, window: int) -> tuple[bool, int]:
    now = time.time()
    dq = store[key]
    # Remove old entries
    while dq and (now - dq[0]) > window:
        dq.popleft()
    if len(dq) >= limit:
        # Time until oldest entry expires
        retry_after = int(dq[0] + window - now) + 1
        return True, max(1, retry_after)
    dq.append(now)
    return False, 0


def _get_ip(request: Request) -> str:
    # Respect X-Forwarded-For if behind proxy (take first)
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def check_rate_limit(request: Request, tier: str = "global"):
    ip = _get_ip(request)
    if tier == "strict":
        limited, retry = _is_limited(_strict_store, f"strict:{ip}", STRICT_LIMIT, STRICT_WINDOW)
        if limited:
            raise HTTPException(status_code=429, detail=f"Rate limited (strict: {STRICT_LIMIT}/min). Retry after {retry}s", headers={"Retry-After": str(retry)})
    elif tier == "auth":
        limited, retry = _is_limited(_auth_store, f"auth:{ip}", AUTH_LIMIT, AUTH_WINDOW)
        if limited:
            raise HTTPException(status_code=429, detail=f"Rate limited (auth: {AUTH_LIMIT}/min). Retry after {retry}s", headers={"Retry-After": str(retry)})
    else:
        limited, retry = _is_limited(_store, ip, GLOBAL_LIMIT, GLOBAL_WINDOW)
        if limited:
            raise HTTPException(status_code=429, detail=f"Rate limited ({GLOBAL_LIMIT}/min). Retry after {retry}s", headers={"Retry-After": str(retry)})


def rate_limit(tier: str = "global"):
    """Decorator for route functions."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find Request object in args
            request = None
            for a in args:
                if isinstance(a, Request):
                    request = a
                    break
            for v in kwargs.values():
                if isinstance(v, Request):
                    request = v
                    break
            if request:
                await check_rate_limit(request, tier)
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Middleware class for global limiting (alternative to dependency)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Global rate limit as middleware (only for non-whitelisted paths)."""

    def __init__(self, app, exclude_paths: list[str] | None = None):
        super().__init__(app)
        self.exclude_paths = set(exclude_paths or ["/docs", "/openapi.json", "/redoc", "/health"])

    async def dispatch(self, request: Request, call_next):
        # Skip docs/health
        path = request.url.path
        if any(path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        # Global check (light)
        ip = _get_ip(request)
        limited, retry = _is_limited(_store, ip, GLOBAL_LIMIT, GLOBAL_WINDOW)
        if limited:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Global rate limit {GLOBAL_LIMIT}/min exceeded"},
                headers={"Retry-After": str(retry)},
            )
        return await call_next(request)


def clear_all():
    """For tests only."""
    _store.clear()
    _strict_store.clear()
    _auth_store.clear()
