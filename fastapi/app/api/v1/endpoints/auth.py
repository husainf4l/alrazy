"""
Authentication endpoints for RazZ Backend Security System.

JWT-based authentication with login, logout, refresh, and user management.
"""
from datetime import timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.auth import (
    create_access_token, create_token_response,
    generate_password_reset_token, verify_password_reset_token
)
from app.core.dependencies import (
    get_current_user, get_current_active_user, get_current_superuser,
    get_user_service
)
from app.models.user import (
    User, UserCreate, UserUpdate, UserPublic, UserLogin,
    Token, PasswordChange, PasswordReset, PasswordResetConfirm
)
from app.services.user_service import UserService

router = APIRouter()


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_create: UserCreate,
    user_service: UserService = Depends(get_user_service)
) -> UserPublic:
    """Register a new user."""
    # Check if user already exists
    existing_user = await user_service.get_user_by_email(user_create.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    existing_username = await user_service.get_user_by_username(user_create.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user
    db_user = await user_service.create_user(user_create)
    return UserPublic.model_validate(db_user)


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service)
) -> Token:
    """Login with username/email and password."""
    user = await user_service.authenticate_user(
        form_data.username, 
        form_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=30)  # settings.jwt_access_token_expire_minutes
    access_token = create_access_token(
        subject=user.username,
        expires_delta=access_token_expires
    )
    
    refresh_token_obj = await user_service.create_refresh_token(user.id)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=30 * 60,  # 30 minutes in seconds
        refresh_token=refresh_token_obj.token
    )


@router.post("/login-json", response_model=Token)
async def login_json(
    user_login: UserLogin,
    user_service: UserService = Depends(get_user_service)
) -> Token:
    """Login with JSON payload (alternative to form-based login)."""
    user = await user_service.authenticate_user(
        user_login.username, 
        user_login.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        subject=user.username,
        expires_delta=access_token_expires
    )
    
    refresh_token_obj = await user_service.create_refresh_token(user.id)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=30 * 60,
        refresh_token=refresh_token_obj.token
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str = Form(),
    user_service: UserService = Depends(get_user_service)
) -> Token:
    """Refresh access token using refresh token."""
    token_obj = await user_service.get_refresh_token(refresh_token)
    
    if not token_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user
    user = await user_service.get_user(token_obj.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        subject=user.username,
        expires_delta=access_token_expires
    )
    
    # Optionally create new refresh token (rotate refresh tokens)
    await user_service.revoke_refresh_token(refresh_token)
    new_refresh_token = await user_service.create_refresh_token(user.id)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=30 * 60,
        refresh_token=new_refresh_token.token
    )


@router.post("/logout")
async def logout(
    refresh_token: str = Form(),
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """Logout user by revoking refresh token."""
    await user_service.revoke_refresh_token(refresh_token)
    return {"message": "Successfully logged out"}


@router.post("/logout-all")
async def logout_all(
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """Logout from all devices by revoking all refresh tokens."""
    revoked_count = await user_service.revoke_all_user_tokens(current_user.id)
    return {"message": f"Successfully logged out from {revoked_count} devices"}


@router.get("/me", response_model=UserPublic)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> UserPublic:
    """Get current user information."""
    return UserPublic.model_validate(current_user)


@router.put("/me", response_model=UserPublic)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
) -> UserPublic:
    """Update current user information."""
    # Don't allow users to change their superuser status
    if user_update.is_superuser is not None and not current_user.is_superuser:
        user_update.is_superuser = None
    
    updated_user = await user_service.update_user(current_user.id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserPublic.model_validate(updated_user)


@router.post("/change-password")
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """Change current user's password."""
    success = await user_service.change_password(
        current_user.id,
        password_change.current_password,
        password_change.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password"
        )
    
    return {"message": "Password changed successfully"}


@router.post("/password-reset")
async def request_password_reset(
    password_reset: PasswordReset,
    user_service: UserService = Depends(get_user_service)
):
    """Request password reset (sends reset token)."""
    user = await user_service.get_user_by_email(password_reset.email)
    
    # Always return success to prevent email enumeration
    if user:
        reset_token = generate_password_reset_token(password_reset.email)
        # In a real application, you would send this token via email
        # For now, we'll just return it (remove this in production)
        return {"message": "Password reset email sent", "reset_token": reset_token}
    
    return {"message": "Password reset email sent"}


@router.post("/password-reset-confirm")
async def confirm_password_reset(
    password_reset_confirm: PasswordResetConfirm,
    user_service: UserService = Depends(get_user_service)
):
    """Confirm password reset with token."""
    email = verify_password_reset_token(password_reset_confirm.token)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    success = await user_service.reset_password(
        email, 
        password_reset_confirm.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "Password reset successfully"}


# Admin endpoints
@router.get("/users", response_model=List[UserPublic])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_superuser),
    user_service: UserService = Depends(get_user_service)
) -> List[UserPublic]:
    """Get all users (admin only)."""
    users = await user_service.get_users(skip=skip, limit=limit)
    return [UserPublic.model_validate(user) for user in users]


@router.get("/users/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    user_service: UserService = Depends(get_user_service)
) -> UserPublic:
    """Get user by ID (admin only)."""
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserPublic.model_validate(user)


@router.put("/users/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_superuser),
    user_service: UserService = Depends(get_user_service)
) -> UserPublic:
    """Update user by ID (admin only)."""
    updated_user = await user_service.update_user(user_id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserPublic.model_validate(updated_user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    user_service: UserService = Depends(get_user_service)
):
    """Delete user by ID (admin only)."""
    success = await user_service.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"message": "User deleted successfully"}


@router.post("/cleanup-tokens")
async def cleanup_expired_tokens(
    current_user: User = Depends(get_current_superuser),
    user_service: UserService = Depends(get_user_service)
):
    """Cleanup expired refresh tokens (admin only)."""
    cleaned_count = await user_service.cleanup_expired_tokens()
    return {"message": f"Cleaned up {cleaned_count} expired tokens"}
