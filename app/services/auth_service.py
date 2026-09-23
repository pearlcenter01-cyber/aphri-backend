from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import bcrypt
from jose import jwt
import uuid
import logging
from uuid import UUID
from app.config import settings
from app.models.user import User
from app.models.profile import Profile
from app.schemas.auth import UserRegister, UserLogin
from app.utils.constants import UserStatus

# Setup logger
logger = logging.getLogger(__name__)

class AuthService:
    """Authentication service for user registration, login, and token management"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        # Bcrypt has a 72-byte limit - truncate if needed
        password_bytes = password[:72].encode('utf-8')
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        plain_bytes = plain_password[:72].encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    
    @staticmethod
    def create_access_token(user_id: str, email: str) -> str:
        """Create a JWT access token"""
        expires = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": str(user_id),
            "email": email,
            "exp": expires,
            "type": "access"
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Create a JWT refresh token"""
        expires = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": str(user_id),
            "exp": expires,
            "type": "refresh"
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode and verify a JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    @staticmethod
    async def verify_token(token: str) -> str | None:
        """Verify a JWT token and return the user ID"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get("sub")
            if not user_id:
                return None
            return user_id
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None
    
    @staticmethod
    async def register_user(db: Session, user_data: UserRegister) -> dict:
        """Register a new user"""
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Convert date_of_birth to datetime if provided
        date_of_birth = None
        if user_data.date_of_birth:
            try:
                date_of_birth = datetime.strptime(user_data.date_of_birth, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD"
                )
        
        # Create new user
        hashed_password = AuthService.hash_password(user_data.password)
        new_user = User(
            id=str(uuid.uuid4()),  # ✅ Explicitly set UUID
            email=user_data.email,
            phone=user_data.phone,
            password_hash=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            date_of_birth=date_of_birth,
            gender=user_data.gender,
            
            # Preferences
            looking_for_gender=user_data.looking_for_gender,
            looking_for=user_data.looking_for,
            vibe=user_data.vibe if hasattr(user_data, 'vibe') else None,
            vibe_subcategories=user_data.vibe_subcategories if hasattr(user_data, 'vibe_subcategories') else None,
            
            # Age Range Preference
            looking_for_age_min=user_data.looking_for_age_min,
            looking_for_age_max=user_data.looking_for_age_max,
            
            # Religion
            religion=user_data.religion if hasattr(user_data, 'religion') else None,
            religion_preferences=user_data.religion_preferences if hasattr(user_data, 'religion_preferences') else None,
            
            # Life Status
            is_single_parent=user_data.is_single_parent if hasattr(user_data, 'is_single_parent') else False,
            is_divorced=user_data.is_divorced if hasattr(user_data, 'is_divorced') else False,
            open_to_single_parent=user_data.open_to_single_parent if hasattr(user_data, 'open_to_single_parent') else True,
            open_to_divorced=user_data.open_to_divorced if hasattr(user_data, 'open_to_divorced') else True,
            open_to_never_married=user_data.open_to_never_married if hasattr(user_data, 'open_to_never_married') else True,
            
            # Custom Questions
            custom_questions=user_data.custom_questions if hasattr(user_data, 'custom_questions') else None,
            
            # Quote
            quote=user_data.quote if hasattr(user_data, 'quote') else None,
            
            # Compatibility Questions (8 Questions)
            q1_core_need=user_data.q1_core_need,
            q2_sex_intimacy=user_data.q2_sex_intimacy,
            q3_conflict=user_data.q3_conflict,
            q4_success_response=user_data.q4_success_response,
            q5_gender_roles=user_data.q5_gender_roles,
            q6_religion=user_data.q6_religion,
            q7_crisis_response=user_data.q7_crisis_response,
            q8_emotional_maturity=user_data.q8_emotional_maturity,
            is_registration_complete=user_data.is_registration_complete,
            photo_reveal_date=datetime.utcnow() + timedelta(hours=24),
            subscription_status=UserStatus.FREE,
        )
        db.add(new_user)
        db.flush()
        
        # Create empty profile for user
        profile = Profile(user_id=new_user.id)
        db.add(profile)
        
        db.commit()
        db.refresh(new_user)

        # ✅ Auto-create matches with 50%+ compatible users
        if user_data.is_registration_complete:                            # ← ADDED
            try:
                from app.services.swipe_service import SwipeService
                from app.models.match import Match
                from sqlalchemy import or_, and_
                
                # ✅ Get all serious users (excluding self)
                other_users = db.query(User).filter(
                    User.id != new_user.id,
                    User.is_active == True,
                    User.looking_for == "Serious Relationship"
                ).all()
                
                print(f"🔍 Checking {len(other_users)} other serious users for matches with {new_user.email}")
                
                for other in other_users:
                    # ✅ Calculate compatibility directly
                    result = SwipeService.calculate_compatibility(new_user, other)
                    score = result['score']
                    
                    print(f"   📊 {new_user.email} vs {other.email}: {score}%")
                    
                    if score >= 50:
                        # Check if match already exists
                        existing = db.query(Match).filter(
                            or_(
                                and_(Match.user_1_id == new_user.id, Match.user_2_id == other.id),
                                and_(Match.user_1_id == other.id, Match.user_2_id == new_user.id)
                            )
                        ).first()
                        if not existing:
                            new_match = Match(
                                id=str(uuid.uuid4()),
                                user_1_id=new_user.id,
                                user_2_id=other.id,
                                user_1_swiped_at=datetime.utcnow(),
                                user_2_swiped_at=datetime.utcnow(),
                                matched_at=datetime.utcnow(),
                                is_active=True
                            )
                            db.add(new_match)
                            print(f"   ✅ Created match between {new_user.email} and {other.email} ({score}%)")
                db.commit()
            except Exception as e:
                logger.error(f"❌ Error auto-creating matches: {e}")
                import traceback
                traceback.print_exc()
                # Don't fail registration if match creation fails
                pass
        
        # Generate tokens
        access_token = AuthService.create_access_token(str(new_user.id), new_user.email)
        refresh_token = AuthService.create_refresh_token(str(new_user.id))
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": str(new_user.id),
            "email": new_user.email,
            "subscription_status": new_user.subscription_status.value,
            "is_registration_complete": new_user.is_registration_complete
        }
    
    @staticmethod
    async def login_user(db: Session, credentials: UserLogin) -> dict:
        """Login a user and return tokens"""
        user = db.query(User).filter(User.email == credentials.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not AuthService.verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        # Update last active
        user.last_active_at = datetime.utcnow()
        db.commit()
        
        # Generate tokens
        access_token = AuthService.create_access_token(str(user.id), user.email)
        refresh_token = AuthService.create_refresh_token(str(user.id))
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": str(user.id),
            "email": user.email,
            "subscription_status": user.subscription_status.value
        }
    
    @staticmethod
    async def refresh_access_token(db: Session, refresh_token: str) -> dict:
        """Refresh access token using refresh token"""
        payload = AuthService.decode_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        
        # ✅ FIX: Use string directly, don't convert to UUID
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        # Generate new tokens
        access_token = AuthService.create_access_token(str(user.id), user.email)
        new_refresh_token = AuthService.create_refresh_token(str(user.id))
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user_id": str(user.id),
            "email": user.email,
            "subscription_status": user.subscription_status.value,
            "is_registration_complete": user.is_registration_complete

        }
    
    @staticmethod
    async def get_current_user(db: Session, token: str) -> User:
        """Get current user from token"""
        # Validate token is not empty
        if not token or not token.strip():
            logger.error("❌ Empty token received")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization token"
            )
        
        # Decode token
        payload = AuthService.decode_token(token)
        
        # 🔍 DEBUG: Log the decoded payload
        logger.info(f"🔍 Decoded token payload: {payload}")
        
        if payload.get("type") != "access":
            logger.error(f"❌ Invalid token type: {payload.get('type')}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        
        # 🔍 DEBUG: Log the user_id
        logger.info(f"🔍 User ID from token: '{user_id}' (type: {type(user_id).__name__})")
        
        # Validate user_id is not empty and not a dict
        if not user_id or user_id == "" or user_id == "{}" or isinstance(user_id, dict):
            logger.error(f"❌ Invalid user_id: '{user_id}' (type: {type(user_id).__name__})")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        # ✅ FIX: Use string directly, don't convert to UUID
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            logger.error(f"❌ User not found: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            logger.error(f"❌ User inactive: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        logger.info(f"✅ User authenticated: {user.id} ({user.email})")
        return user