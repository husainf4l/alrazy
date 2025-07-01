#!/usr/bin/env python3
"""
Database migration script to add admin_user_id column to cameras table
and create camera_user_access table.
"""
import asyncio
import asyncpg
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings

async def migrate_database():
    """Add new columns and tables for enterprise camera management."""
    
    # Create async engine
    engine = create_async_engine(settings.database_url, echo=True)
    
    try:
        async with engine.begin() as conn:
            print("🔄 Starting database migration for enterprise cameras...")
            
            # 1. Add admin_user_id column to cameras table
            try:
                await conn.execute(text("""
                    ALTER TABLE cameras 
                    ADD COLUMN admin_user_id INTEGER REFERENCES users(id);
                """))
                print("✅ Added admin_user_id column to cameras table")
            except Exception as e:
                if "already exists" in str(e) or "duplicate column" in str(e):
                    print("ℹ️  admin_user_id column already exists")
                else:
                    print(f"⚠️  Error adding admin_user_id column: {e}")
            
            # 2. Create camera_user_access table
            try:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS camera_user_access (
                        id SERIAL PRIMARY KEY,
                        camera_id INTEGER NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        access_level VARCHAR(20) DEFAULT 'viewer' NOT NULL,
                        granted_by INTEGER REFERENCES users(id),
                        granted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
                        is_active BOOLEAN DEFAULT true NOT NULL,
                        UNIQUE(camera_id, user_id)
                    );
                """))
                print("✅ Created camera_user_access table")
            except Exception as e:
                print(f"⚠️  Error creating camera_user_access table: {e}")
            
            # 3. Create indexes for better performance
            try:
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_camera_user_access_camera_id 
                    ON camera_user_access(camera_id);
                """))
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_camera_user_access_user_id 
                    ON camera_user_access(user_id);
                """))
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_cameras_admin_user_id 
                    ON cameras(admin_user_id);
                """))
                print("✅ Created database indexes")
            except Exception as e:
                print(f"⚠️  Error creating indexes: {e}")
            
            # 4. Update existing cameras to set admin_user_id = user_id where null
            try:
                await conn.execute(text("""
                    UPDATE cameras 
                    SET admin_user_id = user_id 
                    WHERE admin_user_id IS NULL;
                """))
                print("✅ Updated existing cameras with admin_user_id")
            except Exception as e:
                print(f"⚠️  Error updating existing cameras: {e}")
                
            print("🎉 Database migration completed successfully!")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("Starting migration...")
    try:
        asyncio.run(migrate_database())
    except Exception as e:
        print(f"Migration error: {e}")
        import traceback
        traceback.print_exc()
