#!/usr/bin/env python3
"""
Reset Database Script for RazZ Backend Security System

This script drops all existing tables and recreates them with the new schema.
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from app.core.config import get_settings

# Import all models to register them with SQLModel
from app.models.user import User, RefreshToken, UserAuditLog
from app.models.company import Company, CompanySecuritySettings, UserRole


async def reset_database():
    """Drop and recreate all database tables."""
    settings = get_settings()
    
    # Create engine
    engine = create_async_engine(
        settings.database_url,
        echo=True,  # Show SQL statements
        future=True,
    )
    
    print("🗑️  Dropping all existing tables...")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    
    print("🔨 Creating new tables with updated schema...")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    await engine.dispose()
    print("✅ Database reset completed successfully!")


if __name__ == "__main__":
    asyncio.run(reset_database())
