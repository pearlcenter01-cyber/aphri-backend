from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.auth_service import AuthService
import re

# Public endpoints that don't require authentication
PUBLIC_PATHS = [
    r"^/$",
    r"^/health$",
    r"^/docs",
    r"^/redoc",
    r"^/api/auth/register$",
    r"^/api/auth/login$",
    r"^/api/auth/refresh$",
    r"^/api/payments/webhook$",
    r"^/openapi.json$",
]

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for public paths
        path = request.url.path
        for pattern in PUBLIC_PATHS:
            if re.match(pattern, path):
                return await call_next(request)
        
        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header"
            )
        
        # Extract token
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise ValueError("Invalid authentication scheme")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format. Use: Bearer <token>"
            )
        
        # Verify token
        user_id = await verify_token(token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Attach user_id to request state
        request.state.user_id = user_id
        
        response = await call_next(request)
        return response