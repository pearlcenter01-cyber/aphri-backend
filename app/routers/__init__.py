"""
API Routes for Aphri
"""
from app.routers import auth
from app.routers import profiles
from app.routers import photos
from app.routers import swipes
from app.routers import matches
from app.routers import chat
from app.routers import payments
from app.routers import subscriptions
from app.routers import push
from app.routers import reports

__all__ = [
    "auth",
    "profiles",
    "photos",
    "swipes",
    "matches",
    "chat",
    "payments",
    "subscriptions",
    "push",
    "reports",
]