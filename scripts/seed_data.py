"""
Seed data script to populate database with test users.
Run this after initializing the database to create test users for login.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import SessionLocal, engine
from app.db.base import Base
import bcrypt

# Import all models to ensure they're registered with Base
from app.models import User  # This ensures User table is created


def hash_password(password: str) -> str:
    """Hash password using bcrypt directly (workaround for passlib compatibility)."""
    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_tables():
    """Create all database tables if they don't exist."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables created successfully!")


def seed_users():
    """Create seed users for testing login functionality."""
    db = SessionLocal()
    
    try:
        # Check if users already exist
        existing_user = db.query(User).filter(User.email == "test@example.com").first()
        if existing_user:
            print("[WARNING] Test user already exists. Skipping seed data.")
            return
        
        # Create test users
        test_users = [
            {
                "email": "test@example.com",
                "password": "test123"
            },
            {
                "email": "admin@example.com",
                "password": "admin123"
            }
        ]
        
        print("\nCreating seed users...")
        for user_data in test_users:
            user = User(
                email=user_data["email"],
                hashed_password=hash_password(user_data["password"])
            )
            db.add(user)
            print(f"[OK] Created user: {user_data['email']} (password: {user_data['password']})")
        
        db.commit()
        print("\n[SUCCESS] Seed data created successfully!")
        print("\n[INFO] Test Login Credentials:")
        print("   Email: test@example.com")
        print("   Password: test123")
        print("\n   Email: admin@example.com")
        print("   Password: admin123")
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error creating seed data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("Database Seeding Script")
    print("=" * 50)
    
    # First, ensure tables exist
    create_tables()
    
    # Then, seed users
    seed_users()
    
    print("\n" + "=" * 50)
    print("Done! You can now test login with the credentials above.")
    print("=" * 50)