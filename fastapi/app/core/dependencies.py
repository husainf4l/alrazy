"""
Dependencies for RazZ Backend Security System.

FastAPI dependencies for authentication, database sessions, and security.
"""
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.core.auth import verify_token
from app.models.user import User, TokenData
from app.services.user_service import UserService


"""
FastAPI dependencies for the Al Razy Pharmacy Security System.
"""
from app.core.config import get_settings, Settings


# Security scheme
security = HTTPBearer()


def get_app_settings() -> Settings:
    """Get application settings."""
    return get_settings()


async def get_camera_service():
    """Get async camera service dependency."""
    try:
        from app.services.async_camera_service import get_camera_manager
        return await get_camera_manager()
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Camera service not available"
        )


async def get_security_service():
    """Get security service dependency."""
    try:
        from app.services.security_service import get_security_orchestrator
        return get_security_orchestrator()
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security service not available"
        )


async def get_recording_service():
    """Get recording service dependency."""
    try:
        from app.services.recording_service import get_recording_service
        return get_recording_service()
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recording service not available"
        )


async def get_webhook_service():
    """Get webhook service dependency."""
    try:
        from app.services.webhook_service import get_webhook_service
        return get_webhook_service()
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook service not available"
        )


async def get_llm_service():
    """Get LLM service dependency."""
    try:
        from app.services.llm_service import get_llm_analyzer
        return get_llm_analyzer()
    except ImportError:
        return None  # LLM service is optional


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception
            
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
        token_data = TokenData(username=username)
    except Exception:
        raise credentials_exception
    
    user_service = UserService(session)
    user = await user_service.get_user_by_username_or_email(token_data.username)
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    if not credentials:
        return None
        
    try:
        payload = verify_token(credentials.credentials)
        if payload is None:
            return None
            
        username: str = payload.get("sub")
        if username is None:
            return None
            
        user_service = UserService(session)
        user = await user_service.get_user_by_username_or_email(username)
        
        if user is None or not user.is_active:
            return None
            
        return user
    except Exception:
        return None


def get_user_service(
    session: AsyncSession = Depends(get_session)
) -> UserService:
    """Get user service dependency."""
    return UserService(session)
