"""
Database configuration and session management for RazZ Backend Security System.

Async database connection using SQLModel and PostgreSQL with asyncpg.
"""
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from app.core.config import get_settings

# Import all models to register them with SQLModel
from app.models.user import User, RefreshToken, UserAuditLog
from app.models.company import Company, CompanySecuritySettings, UserRole

settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    future=True,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,  # Recycle connections every 5 minutes
)

# Create async session factory
async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def create_db_and_tables():
    """Create database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def create_tables():
    """Alias for create_db_and_tables for convenience."""
    await create_db_and_tables()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_db_connection():
    """Close database connection."""
    await engine.dispose()
