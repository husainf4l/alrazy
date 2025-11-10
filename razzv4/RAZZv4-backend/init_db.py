"""Database initialization script"""

from sqlalchemy import create_engine
from models import Base
from database import DATABASE_URL

def create_tables():
    """Create all database tables"""
    try:
        engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        
        # Print table info
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"📋 Created tables: {', '.join(tables)}")
        
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")

if __name__ == "__main__":
    create_tables()