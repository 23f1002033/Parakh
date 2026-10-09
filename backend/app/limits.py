import hashlib
import math
import time
from collections import defaultdict, deque

from fastapi import Request

from app.schemas import ApiError

WINDOW_SECONDS = 3600


def ip_hash(salt: str, ip: str) -> str:
    return hashlib.sha256(f"{salt}|{ip}".encode()).hexdigest()


def client_key(request: Request) -> str:
    ip = request.client.host if request.client else ""
    return ip_hash(request.app.state.settings.ip_salt, ip)


class RateLimiter:
    """Sliding one-hour window per salted IP hash, in memory (one process)."""

    def __init__(self, limit: int, what: str, clock=time.monotonic):
        self.limit = limit
        self.what = what
        self.clock = clock
        self.hits: dict[str, deque] = defaultdict(deque)

    def _recent(self, key: str) -> deque:
        hits, now = self.hits[key], self.clock()
        while hits and now - hits[0] >= WINDOW_SECONDS:
            hits.popleft()
        return hits

    def check(self, key: str) -> None:
        hits = self._recent(key)
        if len(hits) >= self.limit:
            retry = max(1, math.ceil(WINDOW_SECONDS - (self.clock() - hits[0])))
            minutes = max(1, math.ceil(retry / 60))
            raise ApiError(
                429, "rate_limited",
                f"You can send {self.limit} {self.what} per hour. Try again in {minutes} minute{'s' if minutes > 1 else ''}.",
                headers={"Retry-After": str(retry)},
            )

    def hit(self, key: str) -> None:
        self._recent(key).append(self.clock())
