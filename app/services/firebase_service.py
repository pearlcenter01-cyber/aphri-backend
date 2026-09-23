import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, status
import logging
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK once
_firebase_initialized = False

def initialize_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return
    try:
        cred = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT)
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        logger.info("✅ Firebase Admin SDK initialized")
    except Exception as e:
        logger.error(f"❌ Firebase init failed: {e}")
        raise


class FirebaseService:
    """Verify Firebase ID tokens from Google Sign-In and Phone Auth"""

    @staticmethod
    def verify_id_token(id_token: str) -> dict:
        """
        Verify a Firebase ID token.
        Returns the decoded token payload with at least:
        - uid
        - phone_number (for phone auth)
        - email, name, picture (for Google auth)
        - firebase.sign_in_provider
        """
        initialize_firebase()
        try:
            decoded = auth.verify_id_token(id_token)
            return decoded
        except auth.ExpiredIdTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Firebase token expired"
            )
        except auth.InvalidIdTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Firebase token"
            )
        except Exception as e:
            logger.error(f"❌ Firebase token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )