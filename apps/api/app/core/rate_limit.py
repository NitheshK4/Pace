import time
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import logger

class RateLimiter:
    """Simple in-memory sliding window rate limiter."""
    def __init__(self, requests_per_minute: int = 120):
        self.requests_per_minute = requests_per_minute
        self.history = defaultdict(list)

    def is_allowed(self, client_identifier: str) -> bool:
        now = time.time()
        window_start = now - 60.0
        
        # Filter timestamps older than 60s
        timestamps = [t for t in self.history[client_identifier] if t > window_start]
        self.history[client_identifier] = timestamps

        if len(timestamps) >= self.requests_per_minute:
            return False

        self.history[client_identifier].append(now)
        return True

    def get_remaining(self, client_identifier: str) -> int:
        now = time.time()
        window_start = now - 60.0
        timestamps = [t for t in self.history[client_identifier] if t > window_start]
        return max(0, self.requests_per_minute - len(timestamps))

ingest_rate_limiter = RateLimiter(requests_per_minute=300)
auth_rate_limiter = RateLimiter(requests_per_minute=30)

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"

        # Apply rate limiting to auth and ingest endpoints
        if request.url.path.startswith("/v1/auth/login"):
            if not auth_rate_limiter.is_allowed(client_ip):
                logger.warning(f"Rate limit exceeded for auth login from IP: {client_ip}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please wait before retrying."
                )

        if request.url.path.startswith("/v1/ingest/events"):
            if not ingest_rate_limiter.is_allowed(client_ip):
                logger.warning(f"Rate limit exceeded for ingestion from IP: {client_ip}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Ingestion rate limit exceeded. Please throttle telemetry batching."
                )

        return await call_next(request)
