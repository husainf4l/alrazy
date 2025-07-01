"""
Company models for RazZ Backend Security System.

SQLModel-based models for company/organization management.
"""
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from pydantic import EmailStr

if TYPE_CHECKING:
    from app.models.user import User


class CompanyBase(SQLModel):
    """Base company model with common fields."""
    name: str = Field(min_length=2, max_length=200, index=True)
    description: Optional[str] = Field(default=None, max_length=1000)
    website: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(default=None, max_length=500)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = Field(default=True)


class Company(CompanyBase, table=True):
    """Company table model."""
    __tablename__ = "companies"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Company settings
    max_users: int = Field(default=50, ge=1, le=1000)
    max_cameras: int = Field(default=10, ge=1, le=100)
    subscription_tier: str = Field(default="basic", regex="^(basic|premium|enterprise)$")
    subscription_expires_at: Optional[datetime] = None
    
    # Relationships
    users: List["User"] = Relationship(back_populates="company")
    security_settings: Optional["CompanySecuritySettings"] = Relationship(back_populates="company")


class CompanyCreate(CompanyBase):
    """Company creation schema."""
    max_users: Optional[int] = Field(default=50, ge=1, le=1000)
    max_cameras: Optional[int] = Field(default=10, ge=1, le=100)
    subscription_tier: Optional[str] = Field(default="basic", regex="^(basic|premium|enterprise)$")


class CompanyUpdate(SQLModel):
    """Company update schema."""
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    website: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(default=None, max_length=500)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    is_active: Optional[bool] = None
    max_users: Optional[int] = Field(default=None, ge=1, le=1000)
    max_cameras: Optional[int] = Field(default=None, ge=1, le=100)
    subscription_tier: Optional[str] = Field(default=None, regex="^(basic|premium|enterprise)$")
    subscription_expires_at: Optional[datetime] = None


class CompanyPublic(CompanyBase):
    """Public company schema (excluding sensitive data)."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    max_users: int
    max_cameras: int
    subscription_tier: str
    subscription_expires_at: Optional[datetime] = None


class CompanyStats(SQLModel):
    """Company statistics schema."""
    total_users: int
    active_users: int
    total_cameras: int
    active_cameras: int
    storage_used_gb: float
    alerts_last_30_days: int


# Company Security Settings
class CompanySecuritySettingsBase(SQLModel):
    """Base security settings for companies."""
    require_2fa: bool = Field(default=False)
    password_expiry_days: Optional[int] = Field(default=None, ge=30, le=365)
    max_login_attempts: int = Field(default=5, ge=3, le=10)
    session_timeout_minutes: int = Field(default=480, ge=30, le=1440)  # 8 hours default
    allowed_ip_ranges: Optional[str] = Field(default=None, max_length=1000)
    require_password_complexity: bool = Field(default=True)
    allow_api_access: bool = Field(default=True)
    
    # Camera access settings
    camera_access_schedule: Optional[str] = Field(default=None, max_length=500)
    record_user_actions: bool = Field(default=True)
    
    # Notification settings
    alert_on_login_failure: bool = Field(default=True)
    alert_on_new_device: bool = Field(default=True)
    alert_on_camera_offline: bool = Field(default=True)


class CompanySecuritySettings(CompanySecuritySettingsBase, table=True):
    """Company security settings table model."""
    __tablename__ = "company_security_settings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    company: Optional[Company] = Relationship(back_populates="security_settings")


class CompanySecuritySettingsCreate(CompanySecuritySettingsBase):
    """Company security settings creation schema."""
    pass


class CompanySecuritySettingsUpdate(SQLModel):
    """Company security settings update schema."""
    require_2fa: Optional[bool] = None
    password_expiry_days: Optional[int] = Field(default=None, ge=30, le=365)
    max_login_attempts: Optional[int] = Field(default=None, ge=3, le=10)
    session_timeout_minutes: Optional[int] = Field(default=None, ge=30, le=1440)
    allowed_ip_ranges: Optional[str] = Field(default=None, max_length=1000)
    require_password_complexity: Optional[bool] = None
    allow_api_access: Optional[bool] = None
    camera_access_schedule: Optional[str] = Field(default=None, max_length=500)
    record_user_actions: Optional[bool] = None
    alert_on_login_failure: Optional[bool] = None
    alert_on_new_device: Optional[bool] = None
    alert_on_camera_offline: Optional[bool] = None


# User Roles within Companies
class UserRole(SQLModel, table=True):
    """User roles within companies."""
    __tablename__ = "user_roles"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    company_id: int = Field(foreign_key="companies.id")
    role: str = Field(regex="^(owner|admin|manager|operator|viewer)$")
    granted_by: Optional[int] = Field(default=None, foreign_key="users.id")
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_active: bool = Field(default=True)
    
    # Permissions
    can_manage_users: bool = Field(default=False)
    can_manage_cameras: bool = Field(default=False)
    can_manage_settings: bool = Field(default=False)
    can_view_analytics: bool = Field(default=True)
    can_export_data: bool = Field(default=False)
    can_manage_alerts: bool = Field(default=False)


class UserRoleCreate(SQLModel):
    """User role creation schema."""
    user_id: int
    company_id: int
    role: str = Field(regex="^(owner|admin|manager|operator|viewer)$")
    expires_at: Optional[datetime] = None
    can_manage_users: bool = Field(default=False)
    can_manage_cameras: bool = Field(default=False)
    can_manage_settings: bool = Field(default=False)
    can_view_analytics: bool = Field(default=True)
    can_export_data: bool = Field(default=False)
    can_manage_alerts: bool = Field(default=False)


class UserRoleUpdate(SQLModel):
    """User role update schema."""
    role: Optional[str] = Field(default=None, regex="^(owner|admin|manager|operator|viewer)$")
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    can_manage_users: Optional[bool] = None
    can_manage_cameras: Optional[bool] = None
    can_manage_settings: Optional[bool] = None
    can_view_analytics: Optional[bool] = None
    can_export_data: Optional[bool] = None
    can_manage_alerts: Optional[bool] = None


class UserRolePublic(SQLModel):
    """Public user role schema."""
    id: int
    user_id: int
    company_id: int
    role: str
    granted_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    can_manage_users: bool
    can_manage_cameras: bool
    can_manage_settings: bool
    can_view_analytics: bool
    can_export_data: bool
    can_manage_alerts: bool
