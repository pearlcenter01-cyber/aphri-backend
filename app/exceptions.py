from fastapi import HTTPException, status

class AphriException(Exception):
    """Base exception for Aphri app"""
    pass

class UserNotFoundError(AphriException):
    """Raised when a user is not found"""
    pass

class InvalidCredentialsError(AphriException):
    """Raised when login credentials are invalid"""
    pass

class UserAlreadyExistsError(AphriException):
    """Raised when trying to register an existing user"""
    pass

class SubscriptionError(AphriException):
    """Raised when subscription related errors occur"""
    pass

class PaymentError(AphriException):
    """Raised when payment processing fails"""
    pass

class PhotoUploadError(AphriException):
    """Raised when photo upload fails"""
    pass

class MatchError(AphriException):
    """Raised when match related errors occur"""
    pass

# FastAPI HTTP Exception wrappers
def raise_http_exception(status_code: int, detail: str):
    raise HTTPException(status_code=status_code, detail=detail)

def raise_not_found(detail: str = "Resource not found"):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

def raise_bad_request(detail: str = "Bad request"):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

def raise_unauthorized(detail: str = "Unauthorized"):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

def raise_forbidden(detail: str = "Forbidden"):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)