#!/usr/bin/env python3
"""
Camera table migration - Add missing camera settings columns
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://husain:tt55oo77@localhost:5432/alrazy")

async def add_camera_settings_columns():
    """Add missing camera settings columns to cameras table."""
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    try:
        async with engine.begin() as conn:
            logger.info("🔧 Adding missing camera settings columns...")
            
            # Add camera settings columns with defaults
            columns_to_add = [
                ("last_connected_at", "TIMESTAMP WITHOUT TIME ZONE"),
                ("resolution_width", "INTEGER DEFAULT 1920"),
                ("resolution_height", "INTEGER DEFAULT 1080"),
                ("fps", "INTEGER DEFAULT 30"),
                ("quality", "INTEGER DEFAULT 80"),
                ("enable_motion_detection", "BOOLEAN DEFAULT true NOT NULL"),
                ("enable_recording", "BOOLEAN DEFAULT true NOT NULL"),
                ("recording_duration", "INTEGER DEFAULT 60 NOT NULL")
            ]
            
            for column_name, column_def in columns_to_add:
                try:
                    await conn.execute(text(f"""
                        ALTER TABLE cameras 
                        ADD COLUMN IF NOT EXISTS {column_name} {column_def};
                    """))
                    logger.info(f"✅ Added column: {column_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Column {column_name} might already exist: {e}")
            
            # Add constraints (ignore if they already exist)
            try:
                await conn.execute(text("""
                    ALTER TABLE cameras 
                    ADD CONSTRAINT check_quality 
                    CHECK (quality >= 1 AND quality <= 100);
                """))
                logger.info("✅ Added quality constraint")
            except Exception as e:
                logger.warning(f"⚠️ Quality constraint might already exist: {e}")
            
            try:
                await conn.execute(text("""
                    ALTER TABLE cameras 
                    ADD CONSTRAINT check_recording_duration 
                    CHECK (recording_duration >= 10 AND recording_duration <= 3600);
                """))
                logger.info("✅ Added recording duration constraint")
            except Exception as e:
                logger.warning(f"⚠️ Recording duration constraint might already exist: {e}")
            
            logger.info("✅ Added column constraints")
            
            # Update existing records to have proper defaults
            await conn.execute(text("""
                UPDATE cameras 
                SET 
                    enable_motion_detection = COALESCE(enable_motion_detection, true),
                    enable_recording = COALESCE(enable_recording, true),
                    recording_duration = COALESCE(recording_duration, 60),
                    resolution_width = COALESCE(resolution_width, 1920),
                    resolution_height = COALESCE(resolution_height, 1080),
                    fps = COALESCE(fps, 30),
                    quality = COALESCE(quality, 80)
                WHERE 
                    enable_motion_detection IS NULL 
                    OR enable_recording IS NULL 
                    OR recording_duration IS NULL;
            """))
            
            logger.info("✅ Updated existing records with defaults")
            
            print("🎉 Camera settings columns migration completed successfully!")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_camera_settings_columns())
