"""
Fix cascade delete for camera deletion
Adds ON DELETE CASCADE to foreign key constraint
"""
from sqlalchemy import create_engine, text
from database import DATABASE_URL

def fix_cascade_delete():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            print("Checking existing constraints...")
            
            # Drop the existing foreign key constraint
            print("Dropping old constraint...")
            conn.execute(text("""
                ALTER TABLE detection_counts 
                DROP CONSTRAINT IF EXISTS detection_counts_camera_id_fkey;
            """))
            
            # Add new constraint with CASCADE
            print("Adding new constraint with CASCADE...")
            conn.execute(text("""
                ALTER TABLE detection_counts 
                ADD CONSTRAINT detection_counts_camera_id_fkey 
                FOREIGN KEY (camera_id) 
                REFERENCES cameras(id) 
                ON DELETE CASCADE;
            """))
            
            trans.commit()
            print("✅ Successfully updated foreign key constraint with CASCADE delete")
            
        except Exception as e:
            trans.rollback()
            print(f"❌ Error updating constraint: {e}")
            raise

if __name__ == "__main__":
    fix_cascade_delete()
