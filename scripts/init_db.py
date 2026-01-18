"""
Database initialization script.
Creates all database tables based on SQLAlchemy models.
Run this before seeding data.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import engine
from app.db.base import Base

# Import all models to ensure they're registered with Base
from app.models import User


def init_db():
    """Initialize database by creating all tables."""
    print("=" * 50)
    print("Database Initialization")
    print("=" * 50)
    print("\nCreating database tables...")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("[SUCCESS] Database tables created successfully!")
        print("\nYou can now run seed_data.py to populate test data.")
    except Exception as e:
        print(f"[ERROR] Error creating tables: {e}")
        raise


if __name__ == "__main__":
    init_db()
