"""IP-based rate limiting for auth endpoints.

Uses a module-level dictionary with sliding-window timestamps.
Five requests per IP per hour is the default limit.

``ip_rate_limit`` can be used in two ways:

    # bare decorator — uses defaults (5 req / 3600 s)
    @ip_rate_limit
    def view(): ...

    # factory — custom limits
    @ip_rate_limit(max_requests=3, window_seconds=86400)
    def view(): ...
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from functools import wraps
from typing import Callable

from flask import jsonify, request

logger = logging.getLogger(__name__)

_WINDOW_SECONDS = 3600  # 1 hour
_MAX_REQUESTS = 5

# ip -> list of epoch timestamps for recent requests
_ip_timestamps: dict[str, list[float]] = defaultdict(list)


def ip_rate_limit(
    fn: Callable | None = None,
    *,
    max_requests: int = _MAX_REQUESTS,
    window_seconds: int = _WINDOW_SECONDS,
) -> Callable:
    """Decorator / decorator factory: enforce sliding-window rate limit per remote IP.

    Returns 429 with a Retry-After header when the limit is exceeded.

    Usage as a bare decorator (preserves existing call sites):

        @ip_rate_limit
        def view(): ...

    Usage as a factory (custom limits):

        @ip_rate_limit(max_requests=3, window_seconds=86400)
        def view(): ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            ip = request.remote_addr or "unknown"
            now = time.time()
            cutoff = now - window_seconds

            # Prune timestamps outside the window
            _ip_timestamps[ip] = [t for t in _ip_timestamps[ip] if t > cutoff]

            # Evict entire dict if it exceeds 10 000 IPs to prevent OOM.
            if len(_ip_timestamps) > 10000:
                _ip_timestamps.clear()

            if len(_ip_timestamps[ip]) >= max_requests:
                oldest = _ip_timestamps[ip][0]
                retry_after = int(window_seconds - (now - oldest)) + 1
                logger.warning("rate limit exceeded for ip=%s", ip)
                response = jsonify({"error": "rate limit exceeded — try again later"})
                response.headers["Retry-After"] = str(retry_after)
                return response, 429

            _ip_timestamps[ip].append(now)
            return func(*args, **kwargs)

        return wrapper

    # Bare-decorator usage: @ip_rate_limit (fn is the wrapped function)
    if fn is not None:
        return decorator(fn)

    # Factory usage: @ip_rate_limit(...) — return the decorator
    return decorator
