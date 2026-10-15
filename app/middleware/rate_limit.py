from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from collections import defaultdict
import time
from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests = defaultdict(list)
        self.register_attempts = defaultdict(list)
        self.limit = settings.RATE_LIMIT_REQUESTS
        self.period = settings.RATE_LIMIT_PERIOD

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Global limit
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if now - t < self.period
        ]
        if len(self.requests[client_ip]) >= self.limit:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Too many requests. Limit: {self.limit} per {self.period}s"
                },
            )
        self.requests[client_ip].append(now)

        # Stricter limit for registration: 3 per hour per IP
        if request.url.path == "/api/auth/register" and request.method == "POST":
            self.register_attempts[client_ip] = [
                t for t in self.register_attempts[client_ip] if now - t < 3600
            ]
            if len(self.register_attempts[client_ip]) >= 3:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too many signups from this network. Please try again later."
                    },
                )
            self.register_attempts[client_ip].append(now)

        return await call_next(request)