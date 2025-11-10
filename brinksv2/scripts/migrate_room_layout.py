"""
Migration script to add room layout fields
Adds dimensions, floor_plan_image, layout_scale, and camera_positions columns
"""
from sqlalchemy import create_engine, text
from database import engine, SessionLocal
from utils.logger import get_logger

logger = get_logger(__name__)


def migrate():
    """Add room layout fields to rooms table"""
    
    migrations = [
        # Add dimensions column (JSON)
        """
        ALTER TABLE rooms 
        ADD COLUMN IF NOT EXISTS dimensions JSON;
        """,
        
        # Add floor_plan_image column (TEXT for base64)
        """
        ALTER TABLE rooms 
        ADD COLUMN IF NOT EXISTS floor_plan_image TEXT;
        """,
        
        # Add layout_scale column (pixels per meter)
        """
        ALTER TABLE rooms 
        ADD COLUMN IF NOT EXISTS layout_scale INTEGER DEFAULT 100;
        """,
        
        # Add camera_positions column (JSON)
        """
        ALTER TABLE rooms 
        ADD COLUMN IF NOT EXISTS camera_positions JSON;
        """
    ]
    
    try:
        with engine.connect() as conn:
            for migration_sql in migrations:
                logger.info(f"Executing: {migration_sql.strip()[:50]}...")
                conn.execute(text(migration_sql))
                conn.commit()
        
        logger.info("✅ Successfully added room layout fields")
        print("✅ Migration completed successfully!")
        print("   Added columns:")
        print("   - dimensions (JSON)")
        print("   - floor_plan_image (TEXT)")
        print("   - layout_scale (INTEGER)")
        print("   - camera_positions (JSON)")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        print(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    print("🔄 Starting room layout migration...")
    migrate()
