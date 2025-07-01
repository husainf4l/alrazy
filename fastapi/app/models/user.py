"""
User models for RazZ Backend Security System.

SQLModel-based models for user authentication and authorization with company support.
"""
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from pydantic import EmailStr

if TYPE_CHECKING:
    from app.models.company import Company, CompanyPublic, UserRole, UserRolePublic


class UserBase(SQLModel):
    """Base user model with common fields."""
    email: EmailStr = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True, min_length=3, max_length=50)
    full_name: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    timezone: Optional[str] = Field(default="UTC", max_length=50)
    language: Optional[str] = Field(default="en", max_length=10)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    company_id: Optional[int] = Field(default=None, foreign_key="companies.id")


class User(UserBase, table=True):
    """User table model."""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(min_length=60, max_length=100)  # bcrypt hash length
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    last_login: Optional[datetime] = Field(default=None)
    
    # Security fields
    failed_login_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = Field(default=None)
    password_changed_at: datetime = Field(default_factory=datetime.utcnow)
    must_change_password: bool = Field(default=False)
    two_factor_enabled: bool = Field(default=False)
    two_factor_secret: Optional[str] = Field(default=None, max_length=100)
    
    # Relationships
    company: Optional["Company"] = Relationship(back_populates="users")
    tokens: List["RefreshToken"] = Relationship(back_populates="user")
    audit_logs: List["UserAuditLog"] = Relationship(back_populates="user")


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(min_length=8, max_length=100)
    company_id: Optional[int] = None


class UserUpdate(SQLModel):
    """User update schema."""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    timezone: Optional[str] = Field(default=None, max_length=50)
    language: Optional[str] = Field(default=None, max_length=10)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    company_id: Optional[int] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=100)
    must_change_password: Optional[bool] = None
    two_factor_enabled: Optional[bool] = None


class UserPublic(UserBase):
    """Public user schema (excluding sensitive data)."""
    id: int
    created_at: datetime
    last_login: Optional[datetime] = None
    password_changed_at: datetime
    must_change_password: bool
    two_factor_enabled: bool
    failed_login_attempts: int


class UserInDB(UserBase):
    """User schema for internal use (with hashed password)."""
    id: int
    hashed_password: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    failed_login_attempts: int
    locked_until: Optional[datetime] = None
    password_changed_at: datetime
    must_change_password: bool
    two_factor_enabled: bool
    two_factor_secret: Optional[str] = None


# Audit Log for user actions
class UserAuditLogBase(SQLModel):
    """Base audit log model."""
    action: str = Field(max_length=100)
    resource_type: Optional[str] = Field(default=None, max_length=50)
    resource_id: Optional[int] = None
    details: Optional[str] = Field(default=None, max_length=1000)
    ip_address: Optional[str] = Field(default=None, max_length=45)  # IPv6 compatible
    user_agent: Optional[str] = Field(default=None, max_length=500)


class UserAuditLog(UserAuditLogBase, table=True):
    """User audit log table model."""
    __tablename__ = "user_audit_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    company_id: Optional[int] = Field(default=None, foreign_key="companies.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="audit_logs")


class UserAuditLogCreate(UserAuditLogBase):
    """User audit log creation schema."""
    user_id: int
    company_id: Optional[int] = None


class UserAuditLogPublic(UserAuditLogBase):
    """Public user audit log schema."""
    id: int
    user_id: int
    company_id: Optional[int]
    timestamp: datetime


# Token models
class TokenBase(SQLModel):
    """Base token model."""
    access_token: str
    token_type: str = "bearer"


class Token(TokenBase):
    """Token response schema."""
    expires_in: int  # seconds until expiration
    refresh_token: Optional[str] = None


class RefreshToken(SQLModel, table=True):
    """Refresh token table model."""
    __tablename__ = "refresh_tokens"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)
    user_id: int = Field(foreign_key="users.id")
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_revoked: bool = Field(default=False)
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="tokens")


class TokenData(SQLModel):
    """Token data schema for JWT payload."""
    username: Optional[str] = None
    user_id: Optional[int] = None
    scopes: List[str] = []


# Login schemas
class UserLogin(SQLModel):
    """User login schema."""
    username: str  # Can be username or email
    password: str


class PasswordChange(SQLModel):
    """Password change schema."""
    current_password: str
    new_password: str = Field(min_length=8, max_length=100)


class PasswordReset(SQLModel):
    """Password reset schema."""
    email: EmailStr


class PasswordResetConfirm(SQLModel):
    """Password reset confirmation schema."""
    token: str
    new_password: str = Field(min_length=8, max_length=100)
