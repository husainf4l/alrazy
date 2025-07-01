"""
User service for RazZ Backend Security System.

CRUD operations and business logic for user management.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlmodel import SQLModel
from app.models.user import (
    User, UserCreate, UserUpdate, UserPublic, UserInDB,
    RefreshToken, TokenData
)
from app.core.auth import (
    get_password_hash, verify_password, create_access_token,
    create_refresh_token, verify_token
)


class UserService:
    """User service for database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, user_create: UserCreate) -> User:
        """Create a new user."""
        hashed_password = get_password_hash(user_create.password)
        
        db_user = User(
            email=user_create.email,
            username=user_create.username,
            full_name=user_create.full_name,
            hashed_password=hashed_password,
            is_active=user_create.is_active,
            is_superuser=user_create.is_superuser,
        )
        
        self.session.add(db_user)
        await self.session.commit()
        await self.session.refresh(db_user)
        return db_user

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_username_or_email(self, identifier: str) -> Optional[User]:
        """Get user by username or email."""
        result = await self.session.execute(
            select(User).where(
                or_(User.username == identifier, User.email == identifier)
            )
        )
        return result.scalar_one_or_none()

    async def get_users(
        self, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[User]:
        """Get multiple users with pagination."""
        query = select(User)
        
        if is_active is not None:
            query = query.where(User.is_active == is_active)
            
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """Update user information."""
        db_user = await self.get_user(user_id)
        if not db_user:
            return None

        update_data = user_update.model_dump(exclude_unset=True)
        
        # Handle password update separately
        if "password" in update_data:
            hashed_password = get_password_hash(update_data.pop("password"))
            update_data["hashed_password"] = hashed_password

        # Update timestamp
        update_data["updated_at"] = datetime.utcnow()

        for field, value in update_data.items():
            setattr(db_user, field, value)

        await self.session.commit()
        await self.session.refresh(db_user)
        return db_user

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user (soft delete by setting is_active=False)."""
        db_user = await self.get_user(user_id)
        if not db_user:
            return False

        db_user.is_active = False
        db_user.updated_at = datetime.utcnow()
        
        await self.session.commit()
        return True

    async def authenticate_user(
        self, 
        username_or_email: str, 
        password: str
    ) -> Optional[User]:
        """Authenticate user with username/email and password."""
        user = await self.get_user_by_username_or_email(username_or_email)
        
        if not user:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
            
        # Update last login
        user.last_login = datetime.utcnow()
        await self.session.commit()
        
        return user

    async def create_refresh_token(
        self, 
        user_id: int, 
        expires_delta: Optional[timedelta] = None
    ) -> RefreshToken:
        """Create a refresh token for a user."""
        if expires_delta is None:
            expires_delta = timedelta(days=30)  # Default 30 days
            
        token_str = create_refresh_token()
        expires_at = datetime.utcnow() + expires_delta
        
        refresh_token = RefreshToken(
            token=token_str,
            user_id=user_id,
            expires_at=expires_at
        )
        
        self.session.add(refresh_token)
        await self.session.commit()
        await self.session.refresh(refresh_token)
        return refresh_token

    async def get_refresh_token(self, token: str) -> Optional[RefreshToken]:
        """Get refresh token by token string."""
        result = await self.session.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.token == token,
                    RefreshToken.is_revoked == False,
                    RefreshToken.expires_at > datetime.utcnow()
                )
            )
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token: str) -> bool:
        """Revoke a refresh token."""
        refresh_token = await self.get_refresh_token(token)
        if not refresh_token:
            return False
            
        refresh_token.is_revoked = True
        await self.session.commit()
        return True

    async def revoke_all_user_tokens(self, user_id: int) -> int:
        """Revoke all refresh tokens for a user."""
        result = await self.session.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.is_revoked == False
                )
            )
        )
        tokens = result.scalars().all()
        
        for token in tokens:
            token.is_revoked = True
            
        await self.session.commit()
        return len(tokens)

    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired refresh tokens."""
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.expires_at <= datetime.utcnow()
            )
        )
        expired_tokens = result.scalars().all()
        
        for token in expired_tokens:
            await self.session.delete(token)
            
        await self.session.commit()
        return len(expired_tokens)

    async def change_password(
        self, 
        user_id: int, 
        current_password: str, 
        new_password: str
    ) -> bool:
        """Change user password."""
        user = await self.get_user(user_id)
        if not user:
            return False
            
        if not verify_password(current_password, user.hashed_password):
            return False
            
        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        
        # Revoke all existing tokens for security
        await self.revoke_all_user_tokens(user_id)
        
        await self.session.commit()
        return True

    async def reset_password(self, email: str, new_password: str) -> bool:
        """Reset user password (for password reset flow)."""
        user = await self.get_user_by_email(email)
        if not user:
            return False
            
        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        
        # Revoke all existing tokens for security
        await self.revoke_all_user_tokens(user.id)
        
        await self.session.commit()
        return True
