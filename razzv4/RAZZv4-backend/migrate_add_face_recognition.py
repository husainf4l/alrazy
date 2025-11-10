"""
Database migration: Add face recognition tables
- Enable pgvector extension
- Create persons table
- Create face_embeddings table with vector(512)
- Create tracking_events table
- Add indexes for performance
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Get DATABASE_URL from environment or construct from components
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fallback to individual components
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "razzv4_db")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def run_migration():
    """Run the face recognition migration"""
    try:
        # Connect to database
        engine = create_engine(DATABASE_URL)
        conn = engine.connect()
        
        print("🚀 Starting face recognition database migration...")
        
        # 1. Enable pgvector extension
        print("\n1️⃣  Enabling pgvector extension...")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
        print("✅ pgvector extension enabled")
        
        # 2. Create persons table
        print("\n2️⃣  Creating persons table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS persons (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
                email VARCHAR(255),
                phone VARCHAR(50),
                employee_id VARCHAR(100),
                department VARCHAR(100),
                notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE
            );
        """))
        conn.commit()
        
        # Add indexes separately for clarity
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_persons_name ON persons(name);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_persons_employee_id ON persons(employee_id) WHERE employee_id IS NOT NULL;"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_persons_company ON persons(company_id) WHERE company_id IS NOT NULL;"))
        conn.commit()
        
        print("✅ persons table created")
        
        # 3. Create face_embeddings table
        print("\n3️⃣  Creating face_embeddings table with vector(512)...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS face_embeddings (
                id SERIAL PRIMARY KEY,
                person_id INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
                embedding vector(512) NOT NULL,
                image_path VARCHAR(500),
                quality_score REAL DEFAULT 0.0,
                source VARCHAR(50) DEFAULT 'enrollment',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.commit()
        
        # Add indexes for face_embeddings
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_face_embeddings_person ON face_embeddings(person_id);"))
        conn.commit()
        
        # Create vector similarity index (IVFFlat for fast similarity search)
        print("   Creating vector similarity index (this may take a moment)...")
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_face_embeddings_vector 
            ON face_embeddings 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """))
        conn.commit()
        
        print("✅ face_embeddings table created with vector index")
        
        # 4. Create tracking_events table
        print("\n4️⃣  Creating tracking_events table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tracking_events (
                id SERIAL PRIMARY KEY,
                room_id INTEGER NOT NULL REFERENCES vault_rooms(id) ON DELETE CASCADE,
                camera_id INTEGER NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
                person_id INTEGER REFERENCES persons(id) ON DELETE SET NULL,
                event_type VARCHAR(50) NOT NULL,
                track_id INTEGER,
                confidence REAL,
                bbox JSONB,
                metadata JSONB,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.commit()
        
        # Add indexes for tracking_events
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tracking_events_room ON tracking_events(room_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tracking_events_camera ON tracking_events(camera_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tracking_events_person ON tracking_events(person_id) WHERE person_id IS NOT NULL;"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tracking_events_type ON tracking_events(event_type);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tracking_events_timestamp ON tracking_events(timestamp DESC);"))
        conn.commit()
        
        # Composite index for common queries
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tracking_events_room_timestamp 
            ON tracking_events(room_id, timestamp DESC);
        """))
        conn.commit()
        
        print("✅ tracking_events table created")
        
        # 5. Create uploads directory for face images
        print("\n5️⃣  Creating uploads directory...")
        os.makedirs("uploads/faces", exist_ok=True)
        print("✅ uploads/faces directory created")
        
        print("\n" + "="*60)
        print("✅ Face recognition migration completed successfully!")
        print("="*60)
        print("\nNew tables created:")
        print("  • persons - Enrolled people in the system")
        print("  • face_embeddings - ArcFace embeddings (512-dim vectors)")
        print("  • tracking_events - Event logs (entry/exit/motion)")
        print("\nNext steps:")
        print("  1. ✅ Dependencies installed (insightface, onnxruntime, pgvector)")
        print("  2. ArcFace model will auto-download on first use")
        print("  3. Start enrolling persons via API or UI")
        
        conn.close()
        engine.dispose()
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    run_migration()
