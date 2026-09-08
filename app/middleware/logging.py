from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aphri")

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(f"➡️  {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"⬅️  {response.status_code} "
            f"{request.method} {request.url.path} "
            f"({process_time:.2f}s)"
        )
        
        response.headers["X-Process-Time"] = str(process_time)
        return response