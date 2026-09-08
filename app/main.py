import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import matches
from app.config import settings
from app.database import engine, Base
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.auth import AuthMiddleware
from app.api import compatibility

# ============================================================
# CREATE DATABASE TABLES (First run only)
# ============================================================
# Uncomment for first run to create tables
Base.metadata.create_all(bind=engine)

# ============================================================
# APP SETUP
# ============================================================
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ============================================================
# MIDDLEWARE
# ============================================================
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
# app.add_middleware(AuthMiddleware)  # Uncomment for production

# ============================================================
# STATIC FILES (for photo serving in development)
# ============================================================
# Create data directory if it doesn't exist
os.makedirs(os.path.join(settings.DATA_DIR, "photos"), exist_ok=True)

# Mount static files for photos
app.mount("/photos", StaticFiles(directory=os.path.join(settings.DATA_DIR, "photos")), name="photos")

# ============================================================
# INCLUDE ROUTERS
# ============================================================
from app.routers import (
    auth,
    profiles,
    photos,
    swipes,
    matches,
    chat,
    payments,
    subscriptions,
    push,
    reports,
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(compatibility.router, prefix="/api/compatibility", tags=["Compatibility"])
app.include_router(profiles.router, prefix="/api/profiles", tags=["Profiles"])
app.include_router(photos.router, prefix="/api/photos", tags=["Photos"])
app.include_router(swipes.router, prefix="/api/swipes", tags=["Swipes"])
app.include_router(matches.router, prefix="/api/matches", tags=["Matches"])  # ✅ CORRECT
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["Subscriptions"])
app.include_router(push.router, prefix="/api/push", tags=["Push Notifications"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
# ❌ DELETE THIS: app.include_router(matches.router, prefix="/api", tags=["matches"])
# ============================================================
# WEBSOCKET ROUTES
# ============================================================
from app.websockets.chat_handler import handle_chat_websocket
from app.websockets.typing_handler import handle_typing_websocket
from app.websockets.presence_handler import handle_presence_websocket

@app.websocket("/ws/chat/{match_id}")
async def websocket_chat(websocket: WebSocket, match_id: str):
    """WebSocket endpoint for real-time chat in a match"""
    await handle_chat_websocket(websocket, match_id)

@app.websocket("/ws/typing/{match_id}")
async def websocket_typing(websocket: WebSocket, match_id: str):
    """WebSocket endpoint for typing indicators in a match"""
    await handle_typing_websocket(websocket, match_id)

@app.websocket("/ws/presence")
async def websocket_presence(websocket: WebSocket):
    """WebSocket endpoint for user presence (online/offline status)"""
    await handle_presence_websocket(websocket)

# ============================================================
# ROOT & HEALTH ENDPOINTS
# ============================================================
@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs" if settings.DEBUG else "disabled",
        "endpoints": {
            "auth": "/api/auth",
            "profiles": "/api/profiles",
            "photos": "/api/photos",
            "swipes": "/api/swipes",
            "matches": "/api/matches",
            "chat": "/api/chat",
            "payments": "/api/payments",
            "subscriptions": "/api/subscriptions",
            "push": "/api/push",
            "reports": "/api/reports",
            "websocket_chat": "ws://localhost:8000/ws/chat/{match_id}?token={jwt_token}",
            "websocket_typing": "ws://localhost:8000/ws/typing/{match_id}?token={jwt_token}",
            "websocket_presence": "ws://localhost:8000/ws/presence?token={jwt_token}",
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "connected",
        "websockets": {
            "chat": "/ws/chat/{match_id}",
            "typing": "/ws/typing/{match_id}",
            "presence": "/ws/presence",
        }
    }

# ============================================================
# RUN (for development only)
# ============================================================
if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("❤️  Aphri - Dating App Backend")
    print("=" * 60)
    print(f"📱 App: {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"🌐 Server: http://localhost:8000")
    print(f"📚 Docs: http://localhost:8000/docs")
    print(f"📡 WebSocket Chat: ws://localhost:8000/ws/chat/{{match_id}}?token={{jwt_token}}")
    print(f"📡 WebSocket Typing: ws://localhost:8000/ws/typing/{{match_id}}?token={{jwt_token}}")
    print(f"📡 WebSocket Presence: ws://localhost:8000/ws/presence?token={{jwt_token}}")
    print(f"💳 Payments: Chapa Gateway")
    print("=" * 60)
    print("")
    print("⚠️  To test WebSocket connections, include JWT token in query params:")
    print("   Example: ws://localhost:8000/ws/chat/123?token=your_jwt_token")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )