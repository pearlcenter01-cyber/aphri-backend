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
        self.limit = settings.RATE_LIMIT_REQUESTS
        self.period = settings.RATE_LIMIT_PERIOD

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"

        now = time.time()
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < self.period
        ]

        if len(self.requests[client_ip]) >= self.limit:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Too many requests. Limit: {self.limit} per {self.period}s"
                },
            )

        self.requests[client_ip].append(now)

        response = await call_next(request)
        return response