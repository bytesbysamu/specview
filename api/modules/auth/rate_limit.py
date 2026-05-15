"""IP-based rate limiting for auth endpoints.

Uses a module-level dictionary with sliding-window timestamps.
Five requests per IP per hour is the default limit.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from functools import wraps
from typing import Callable

from flask import jsonify, request

logger = logging.getLogger(__name__)

_WINDOW_SECONDS = 900   # 15 minutes
_MAX_REQUESTS = 15

# ip -> list of epoch timestamps for recent requests
_ip_timestamps: dict[str, list[float]] = defaultdict(list)


def ip_rate_limit(fn: Callable) -> Callable:
    """Decorator: enforce sliding-window rate limit per remote IP.

    Returns 429 with a Retry-After header when the limit is exceeded.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        ip = request.remote_addr or "unknown"
        now = time.time()
        cutoff = now - _WINDOW_SECONDS

        # Prune timestamps outside the window
        _ip_timestamps[ip] = [t for t in _ip_timestamps[ip] if t > cutoff]

        if len(_ip_timestamps[ip]) >= _MAX_REQUESTS:
            oldest = _ip_timestamps[ip][0]
            retry_after = int(_WINDOW_SECONDS - (now - oldest)) + 1
            logger.warning("rate limit exceeded for ip=%s", ip)
            response = jsonify({"error": "rate limit exceeded — try again later"})
            response.headers["Retry-After"] = str(retry_after)
            return response, 429

        _ip_timestamps[ip].append(now)
        return fn(*args, **kwargs)

    return wrapper
