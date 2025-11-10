#!/usr/bin/env python3
"""
Migration: Add detected_persons table for cross-camera person tracking
"""

from sqlalchemy import create_engine, text
from config import get_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

def run_migration():
    """Add detected_persons table"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if table already exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'detected_persons'
            );
        """))
        
        if result.scalar():
            logger.info("✅ Table 'detected_persons' already exists")
            return
        
        logger.info("Creating 'detected_persons' table...")
        
        # Create the table
        conn.execute(text("""
            CREATE TABLE detected_persons (
                id SERIAL PRIMARY KEY,
                global_id INTEGER UNIQUE NOT NULL,
                person_id INTEGER REFERENCES persons(id) ON DELETE SET NULL,
                
                -- Name assignment
                assigned_name VARCHAR(255),
                
                -- Face data
                face_embedding vector(512),
                face_quality FLOAT DEFAULT 0.0,
                
                -- Physical dimensions
                avg_height_pixels FLOAT,
                avg_width_pixels FLOAT,
                avg_height_meters FLOAT,
                
                -- Tracking metadata
                first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                total_appearances INTEGER DEFAULT 1,
                cameras_visited JSONB DEFAULT '[]'::jsonb,
                
                -- Current state
                is_active BOOLEAN DEFAULT TRUE,
                current_room_id INTEGER REFERENCES vault_rooms(id),
                current_positions JSONB DEFAULT '{}'::jsonb,
                
                -- Statistics
                total_detections INTEGER DEFAULT 0,
                quality_scores JSONB DEFAULT '[]'::jsonb,
                
                -- Timestamps
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """))
        
        # Create indexes
        logger.info("Creating indexes...")
        
        conn.execute(text("""
            CREATE INDEX idx_detected_persons_global_id ON detected_persons(global_id);
            CREATE INDEX idx_detected_persons_person_id ON detected_persons(person_id);
            CREATE INDEX idx_detected_persons_first_seen ON detected_persons(first_seen);
            CREATE INDEX idx_detected_persons_last_seen ON detected_persons(last_seen);
            CREATE INDEX idx_detected_persons_is_active ON detected_persons(is_active);
        """))
        
        # Create vector index for face embeddings (IVFFlat for similarity search)
        logger.info("Creating vector index for face embeddings...")
        
        conn.execute(text("""
            CREATE INDEX idx_detected_persons_face_embedding 
            ON detected_persons 
            USING ivfflat (face_embedding vector_cosine_ops)
            WITH (lists = 100);
        """))
        
        conn.commit()
        
        logger.info("✅ Migration completed successfully!")
        logger.info("")
        logger.info("New table 'detected_persons' created with:")
        logger.info("  • Global person tracking across cameras")
        logger.info("  • Face embeddings for re-identification")
        logger.info("  • Physical dimensions (height, width)")
        logger.info("  • Camera visit history")
        logger.info("  • Real-time positions per camera")
        logger.info("  • Vector similarity search support")


if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
