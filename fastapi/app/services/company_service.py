"""
Company service for RazZ Backend Security System.

CRUD operations and business logic for company management.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlmodel import SQLModel

from app.models.company import (
    Company, CompanyCreate, CompanyUpdate, CompanyPublic,
    CompanySecuritySettings, CompanySecuritySettingsCreate, CompanySecuritySettingsUpdate,
    UserRole, UserRoleCreate, UserRoleUpdate, UserRolePublic,
    CompanyStats
)
from app.models.user import User, UserAuditLog


class CompanyService:
    """Company service for database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_company(self, company_create: CompanyCreate) -> Company:
        """Create a new company."""
        db_company = Company(
            name=company_create.name,
            description=company_create.description,
            website=company_create.website,
            phone=company_create.phone,
            email=company_create.email,
            address=company_create.address,
            city=company_create.city,
            state=company_create.state,
            country=company_create.country,
            postal_code=company_create.postal_code,
            is_active=company_create.is_active,
            max_users=company_create.max_users or 50,
            max_cameras=company_create.max_cameras or 10,
            subscription_tier=company_create.subscription_tier or "basic"
        )
        
        self.session.add(db_company)
        await self.session.commit()
        await self.session.refresh(db_company)
        
        # Create default security settings
        await self.create_default_security_settings(db_company.id)
        
        return db_company

    async def get_company(self, company_id: int) -> Optional[Company]:
        """Get company by ID."""
        result = await self.session.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_company_by_name(self, name: str) -> Optional[Company]:
        """Get company by name."""
        result = await self.session.execute(
            select(Company).where(Company.name == name)
        )
        return result.scalar_one_or_none()

    async def get_companies(
        self, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None,
        subscription_tier: Optional[str] = None
    ) -> List[Company]:
        """Get multiple companies with pagination and filters."""
        query = select(Company)
        
        if is_active is not None:
            query = query.where(Company.is_active == is_active)
        
        if subscription_tier:
            query = query.where(Company.subscription_tier == subscription_tier)
            
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_company(self, company_id: int, company_update: CompanyUpdate) -> Optional[Company]:
        """Update company information."""
        db_company = await self.get_company(company_id)
        if not db_company:
            return None

        update_data = company_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(timezone.utc)

        for field, value in update_data.items():
            setattr(db_company, field, value)

        await self.session.commit()
        await self.session.refresh(db_company)
        return db_company

    async def delete_company(self, company_id: int) -> bool:
        """Delete a company (soft delete by setting is_active=False)."""
        db_company = await self.get_company(company_id)
        if not db_company:
            return False

        db_company.is_active = False
        db_company.updated_at = datetime.now(timezone.utc)
        
        await self.session.commit()
        return True

    # Security Settings Management
    async def create_default_security_settings(self, company_id: int) -> CompanySecuritySettings:
        """Create default security settings for a company."""
        settings_create = CompanySecuritySettingsCreate()
        
        security_settings = CompanySecuritySettings(
            company_id=company_id,
            **settings_create.model_dump()
        )
        
        self.session.add(security_settings)
        await self.session.commit()
        await self.session.refresh(security_settings)
        return security_settings

    async def get_company_security_settings(self, company_id: int) -> Optional[CompanySecuritySettings]:
        """Get security settings for a company."""
        result = await self.session.execute(
            select(CompanySecuritySettings).where(CompanySecuritySettings.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def update_company_security_settings(
        self, 
        company_id: int, 
        settings_update: CompanySecuritySettingsUpdate
    ) -> Optional[CompanySecuritySettings]:
        """Update company security settings."""
        db_settings = await self.get_company_security_settings(company_id)
        if not db_settings:
            return None

        update_data = settings_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(timezone.utc)

        for field, value in update_data.items():
            setattr(db_settings, field, value)

        await self.session.commit()
        await self.session.refresh(db_settings)
        return db_settings

    # User Role Management
    async def assign_user_role(
        self, 
        user_role_create: UserRoleCreate,
        granted_by_user_id: int
    ) -> UserRole:
        """Assign a role to a user in a company."""
        # Check if user already has a role in this company
        existing_role = await self.get_user_role(user_role_create.user_id, user_role_create.company_id)
        if existing_role:
            # Deactivate existing role
            existing_role.is_active = False
            
        # Set default permissions based on role
        permissions = self._get_default_role_permissions(user_role_create.role)
        
        user_role = UserRole(
            user_id=user_role_create.user_id,
            company_id=user_role_create.company_id,
            role=user_role_create.role,
            granted_by=granted_by_user_id,
            expires_at=user_role_create.expires_at,
            **permissions
        )
        
        self.session.add(user_role)
        await self.session.commit()
        await self.session.refresh(user_role)
        return user_role

    async def get_user_role(self, user_id: int, company_id: int) -> Optional[UserRole]:
        """Get active user role in a company."""
        result = await self.session.execute(
            select(UserRole).where(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.company_id == company_id,
                    UserRole.is_active == True,
                    or_(
                        UserRole.expires_at.is_(None),
                        UserRole.expires_at > datetime.now(timezone.utc)
                    )
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_company_users(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all users in a company with their roles."""
        result = await self.session.execute(
            select(User, UserRole)
            .join(UserRole, User.id == UserRole.user_id)
            .where(
                and_(
                    UserRole.company_id == company_id,
                    UserRole.is_active == True,
                    User.is_active == True
                )
            )
        )
        
        users_with_roles = []
        for user, role in result.all():
            users_with_roles.append({
                "user": user,
                "role": role
            })
        
        return users_with_roles

    async def update_user_role(
        self, 
        user_id: int, 
        company_id: int, 
        role_update: UserRoleUpdate
    ) -> Optional[UserRole]:
        """Update user role in a company."""
        user_role = await self.get_user_role(user_id, company_id)
        if not user_role:
            return None

        update_data = role_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(user_role, field, value)

        await self.session.commit()
        await self.session.refresh(user_role)
        return user_role

    async def revoke_user_role(self, user_id: int, company_id: int) -> bool:
        """Revoke user role in a company."""
        user_role = await self.get_user_role(user_id, company_id)
        if not user_role:
            return False

        user_role.is_active = False
        await self.session.commit()
        return True

    # Statistics and Analytics
    async def get_company_stats(self, company_id: int) -> CompanyStats:
        """Get company statistics."""
        # Count total users
        total_users_result = await self.session.execute(
            select(func.count(User.id))
            .join(UserRole, User.id == UserRole.user_id)
            .where(UserRole.company_id == company_id)
        )
        total_users = total_users_result.scalar() or 0

        # Count active users
        active_users_result = await self.session.execute(
            select(func.count(User.id))
            .join(UserRole, User.id == UserRole.user_id)
            .where(
                and_(
                    UserRole.company_id == company_id,
                    User.is_active == True,
                    UserRole.is_active == True
                )
            )
        )
        active_users = active_users_result.scalar() or 0

        # Count alerts in last 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        alerts_result = await self.session.execute(
            select(func.count(UserAuditLog.id))
            .where(
                and_(
                    UserAuditLog.company_id == company_id,
                    UserAuditLog.timestamp >= thirty_days_ago,
                    UserAuditLog.action.like('%alert%')
                )
            )
        )
        alerts_count = alerts_result.scalar() or 0

        return CompanyStats(
            total_users=total_users,
            active_users=active_users,
            total_cameras=0,  # TODO: Implement camera counting
            active_cameras=0,  # TODO: Implement active camera counting
            storage_used_gb=0.0,  # TODO: Implement storage calculation
            alerts_last_30_days=alerts_count
        )

    async def check_user_permission(
        self, 
        user_id: int, 
        company_id: int, 
        permission: str
    ) -> bool:
        """Check if user has a specific permission in a company."""
        user_role = await self.get_user_role(user_id, company_id)
        if not user_role:
            return False

        permission_mapping = {
            "manage_users": user_role.can_manage_users,
            "manage_cameras": user_role.can_manage_cameras,
            "manage_settings": user_role.can_manage_settings,
            "view_analytics": user_role.can_view_analytics,
            "export_data": user_role.can_export_data,
            "manage_alerts": user_role.can_manage_alerts
        }
        
        return permission_mapping.get(permission, False)

    def _get_default_role_permissions(self, role: str) -> Dict[str, bool]:
        """Get default permissions for a role."""
        role_permissions = {
            "owner": {
                "can_manage_users": True,
                "can_manage_cameras": True,
                "can_manage_settings": True,
                "can_view_analytics": True,
                "can_export_data": True,
                "can_manage_alerts": True
            },
            "admin": {
                "can_manage_users": True,
                "can_manage_cameras": True,
                "can_manage_settings": True,
                "can_view_analytics": True,
                "can_export_data": True,
                "can_manage_alerts": True
            },
            "manager": {
                "can_manage_users": False,
                "can_manage_cameras": True,
                "can_manage_settings": False,
                "can_view_analytics": True,
                "can_export_data": True,
                "can_manage_alerts": True
            },
            "operator": {
                "can_manage_users": False,
                "can_manage_cameras": False,
                "can_manage_settings": False,
                "can_view_analytics": True,
                "can_export_data": False,
                "can_manage_alerts": True
            },
            "viewer": {
                "can_manage_users": False,
                "can_manage_cameras": False,
                "can_manage_settings": False,
                "can_view_analytics": True,
                "can_export_data": False,
                "can_manage_alerts": False
            }
        }
        
        return role_permissions.get(role, role_permissions["viewer"])
