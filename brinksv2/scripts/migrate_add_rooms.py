"""
Database migration script to add Room support and cross-camera tracking
Run this to upgrade your existing database
"""

from sqlalchemy import create_engine, inspect, text
from database import DATABASE_URL

def migrate_database():
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    print("🔄 Starting database migration...")
    
    with engine.connect() as conn:
        # Check if rooms table exists
        if 'rooms' not in inspector.get_table_names():
            print("📦 Creating rooms table...")
            conn.execute(text("""
                CREATE TABLE rooms (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR NOT NULL UNIQUE,
                    description TEXT,
                    floor_level VARCHAR,
                    capacity INTEGER,
                    overlap_config JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("✅ rooms table created")
        else:
            print("✓ rooms table already exists")
        
        # Check if cameras table has new columns
        camera_columns = [col['name'] for col in inspector.get_columns('cameras')]
        
        if 'room_id' not in camera_columns:
            print("📦 Adding room_id column to cameras...")
            conn.execute(text("ALTER TABLE cameras ADD COLUMN room_id INTEGER REFERENCES rooms(id)"))
            conn.commit()
            print("✅ room_id column added")
        else:
            print("✓ room_id column already exists")
        
        if 'position_config' not in camera_columns:
            print("📦 Adding position_config column to cameras...")
            conn.execute(text("ALTER TABLE cameras ADD COLUMN position_config JSONB"))
            conn.commit()
            print("✅ position_config column added")
        else:
            print("✓ position_config column already exists")
        
        if 'overlap_zones' not in camera_columns:
            print("📦 Adding overlap_zones column to cameras...")
            conn.execute(text("ALTER TABLE cameras ADD COLUMN overlap_zones JSONB"))
            conn.commit()
            print("✅ overlap_zones column added")
        else:
            print("✓ overlap_zones column already exists")
    
    print("🎉 Database migration completed successfully!")
    print("\n📝 Next steps:")
    print("1. Restart your application: pm2 restart all")
    print("2. Visit /rooms-page to create rooms and assign cameras")
    print("3. Configure overlap zones for cameras in the same room")

if __name__ == "__main__":
    migrate_database()
