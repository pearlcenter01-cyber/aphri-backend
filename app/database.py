from sqlalchemy import create_engine, TypeDecorator, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from uuid import UUID as PythonUUID, uuid4
from app.config import settings

# ============================================================
# CUSTOM UUID TYPE FOR SQLITE (PRESERVES HYPHENS)
# ============================================================
class UUIDType(TypeDecorator):
    """Custom UUID type that preserves hyphens for SQLite."""
    impl = String(36)
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, PythonUUID):
            return str(value)  # Preserves hyphens
        if isinstance(value, str):
            # Try to parse as UUID to validate, then return as string
            try:
                PythonUUID(value)
                return value
            except ValueError:
                return None
        return str(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # Return as string (not UUID object)
        return value

# ============================================================
# DATABASE ENGINE
# ============================================================
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# ============================================================
# SESSION LOCAL
# ============================================================
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ============================================================
# BASE MODEL
# ============================================================
Base = declarative_base()

# ============================================================
# DEPENDENCY FOR FASTAPI
# ============================================================
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()