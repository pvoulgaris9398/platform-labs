"""In-memory sliding-window rate limiting suitable for the POC."""

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.config import get_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce per-identity and global request limits over 60 seconds."""

    def __init__(self, app: object) -> None:
        super().__init__(app)
        self.events: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        now = time.monotonic()
        identity = getattr(request.state, "user", None)
        key = (
            identity.principal_arn
            if identity
            else request.client.host
            if request.client
            else "unknown"
        )
        settings = get_settings()
        for bucket, limit in (
            (key, settings.rate_limit_per_minute),
            ("__global__", settings.global_rate_limit_per_minute),
        ):
            timestamps = self.events[bucket]
            while timestamps and timestamps[0] <= now - 60:
                timestamps.popleft()
            if len(timestamps) >= limit:
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": "60"},
                    content={
                        "data": None,
                        "error": {
                            "code": "RATE_LIMITED",
                            "message": "Rate limit exceeded",
                            "details": [],
                        },
                    },
                )
            timestamps.append(now)
        return await call_next(request)
