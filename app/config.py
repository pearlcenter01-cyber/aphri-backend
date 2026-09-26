import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Application settings loaded from environment variables"""
    
    # ============================================================
    # APP SETTINGS
    # ============================================================
    APP_NAME: str = os.getenv("APP_NAME", "Aphri")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    APP_DESCRIPTION: str = "Dating App - Match, Chat, Connect"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-in-production")
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    DATA_DIR: str = os.getenv("DATA_DIR", "./data")
    FIREBASE_SERVICE_ACCOUNT: str = os.getenv("FIREBASE_SERVICE_ACCOUNT", "./firebase-service-account.json")
    
    # ============================================================
    # DATABASE
    # ============================================================
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./data/aphri.db"
    )
    
    # ============================================================
    # JWT AUTHENTICATION
    # ============================================================
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ============================================================
    # OPENAI - AI COMPATIBILITY FEATURE
    # ============================================================
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # or gpt-3.5-turbo for testing
    
    # ============================================================
    # CHAPA PAYMENT
    # ============================================================
    CHAPA_PUBLIC_KEY: str = os.getenv("CHAPA_PUBLIC_KEY", "")
    CHAPA_SECRET_KEY: str = os.getenv("CHAPA_SECRET_KEY", "")
    CHAPA_WEBHOOK_SECRET: str = os.getenv("CHAPA_WEBHOOK_SECRET", "")
    CHAPA_API_URL: str = "https://api.chapa.co/v1"
    
    # ============================================================
    # AWS S3 - PHOTO STORAGE
    # ============================================================
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_BUCKET_NAME: str = os.getenv("AWS_BUCKET_NAME", "aphri-photos")
    
    # ============================================================
    # PUSH NOTIFICATIONS
    # ============================================================
    FCM_SERVER_KEY: str = os.getenv("FCM_SERVER_KEY", "")
    APNS_KEY_ID: str = os.getenv("APNS_KEY_ID", "")
    APNS_TEAM_ID: str = os.getenv("APNS_TEAM_ID", "")
    APNS_AUTH_KEY: str = os.getenv("APNS_AUTH_KEY", "")
    
    # ============================================================
    # CORS
    # ============================================================
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:19000,http://localhost:19006,https://4285-196-189-154-125.ngrok-free.app,https://*.ngrok-free.app"
    ).split(",")
    
    # ============================================================
    # RATE LIMITING
    # ============================================================
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "60"))
    
    # ============================================================
    # SUBSCRIPTION PLANS (in ETB)
    # ============================================================
    PLANS = {
        "starter": {
            "price": 300,
            "usd_display": 2.30,
            "name": "Starter",
            "duration_days": 30,
            "credits": 300,
            "description": "300 credits valid for 30 days"
        },
        "standard": {
            "price": 500,
            "usd_display": 3.85,
            "name": "Standard",
            "duration_days": 30,
            "credits": 500,
            "description": "500 credits valid for 30 days"
        },
        "premium": {
            "price": 1500,
            "usd_display": 11.50,
            "name": "Premium",
            "duration_days": 180,
            "credits": -1,  # -1 = unlimited
            "description": "Unlimited credits for 6 months"
        },
    }

    # ============================================================
    # CREDIT COSTS  (1 ETB = 1 credit)
    # ============================================================
    CREDIT_COST_ANSWER_QUESTIONS = 2
    CREDIT_COST_RATE_ANSWERS = 2

    # ============================================================
    # FEATURE TIERS
    # ============================================================
    FREE_TIER = {
        "max_photos": 999,  # Effectively unlimited
        "max_swipes_per_day": 10,
        "can_message": True,
        "see_who_liked_you": False,
        "read_receipts": False,
        "advanced_filters": False,
        "unlimited_swipes": False,
    }
    
    PREMIUM_TIER = {
        "max_photos": 999,  # Effectively unlimited
        "max_swipes_per_day": None,  # Unlimited
        "can_message": True,
        "see_who_liked_you": True,
        "read_receipts": True,
        "advanced_filters": True,
        "unlimited_swipes": True,
    }


settings = Settings()