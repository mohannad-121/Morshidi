"""In-memory rate limiter for login and sensitive auth endpoints.

NOTE ON PRODUCTION DISTRIBUTED ARCHITECTURE:
This limiter maintains state in process memory. It provides protection against brute-force
attempts in single-instance and local test environments. In distributed or multi-instance
production environments (e.g., behind Cloudflare, Render, or Kubernetes ingress), rate
limiting should be enforced at the edge/reverse proxy or backed by a distributed store (e.g. Redis).
"""

from __future__ import annotations

import collections
import logging
import time
from typing import DefaultDict, Deque

from fastapi import Request

logger = logging.getLogger(__name__)


def extract_client_ip(request: Request) -> str:
    """Safely extract client IP for rate limiting.

    To prevent IP spoofing, arbitrary X-Forwarded-For headers from untrusted direct
    clients are NOT blindly trusted. By default, the direct TCP peer (request.client.host)
    is used.
    """
    if request.client and request.client.host:
        return request.client.host.strip()
    return "127.0.0.1"


class InMemoryLoginRateLimiter:
    """Sliding-window in-memory rate limiter per IP address."""

    def __init__(self, max_attempts: int = 10, window_seconds: int = 60) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        # Maps IP -> deque of timestamps
        self._history: DefaultDict[str, Deque[float]] = collections.defaultdict(collections.deque)

    def check_rate_limit(self, client_ip: str) -> tuple[bool, int]:
        """Check if an attempt is permitted for this IP.

        Returns (is_allowed, retry_after_seconds).
        If allowed, records the attempt timestamp.
        """
        now = time.monotonic()
        history = self._history[client_ip]

        # Evict timestamps outside sliding window
        cutoff = now - self.window_seconds
        while history and history[0] < cutoff:
            history.popleft()

        if len(history) >= self.max_attempts:
            # Exceeded limit; calculate retry_after based on earliest timestamp
            earliest = history[0]
            retry_after = max(1, int(self.window_seconds - (now - earliest)))
            logger.warning("Rate limit exceeded for client IP %s (retry_after=%ds)", client_ip, retry_after)
            return False, retry_after

        # Record attempt
        history.append(now)
        return True, 0

    def reset(self) -> None:
        """Clear all rate limit history (primarily for test isolation)."""
        self._history.clear()


# Default global instance
default_login_rate_limiter = InMemoryLoginRateLimiter(max_attempts=10, window_seconds=60)
