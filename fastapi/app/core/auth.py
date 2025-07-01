"""
Authentication utilities for RazZ Backend Security System.

JWT token creation, verification, and password hashing utilities.
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.hash import bcrypt
from app.core.config import get_settings

settings = get_settings()

# Password hashing context - use specific bcrypt configuration to avoid version issues
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__rounds=12,
    bcrypt__ident="2b"
)


def create_access_token(
    subject: Union[str, int], 
    expires_delta: Optional[timedelta] = None,
    scopes: list = None
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(timezone.utc),
        "type": "access"
    }
    
    if scopes:
        to_encode["scopes"] = scopes
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.jwt_secret_key, 
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_refresh_token() -> str:
    """Create a secure refresh token."""
    return secrets.token_urlsafe(32)


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_password_reset_token(email: str) -> str:
    """Generate a password reset token."""
    delta = timedelta(hours=24)  # Reset tokens expire in 24 hours
    now = datetime.now(timezone.utc)
    expires = now + delta
    
    to_encode = {
        "exp": expires,
        "sub": email,
        "iat": now,
        "type": "password_reset"
    }
    
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )


def verify_password_reset_token(token: str) -> Optional[str]:
    """Verify a password reset token and return the email."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        if payload.get("type") != "password_reset":
            return None
            
        email: str = payload.get("sub")
        if email is None:
            return None
            
        return email
    except JWTError:
        return None


def create_token_response(
    access_token: str,
    refresh_token: Optional[str] = None,
    expires_in: Optional[int] = None
) -> dict:
    """Create a standardized token response."""
    if expires_in is None:
        expires_in = settings.jwt_access_token_expire_minutes * 60
    
    response = {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in
    }
    
    if refresh_token:
        response["refresh_token"] = refresh_token
    
    return response
