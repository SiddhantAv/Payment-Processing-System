"""
Test database connection script.
Use this to verify your DATABASE_URL is correct before running seed scripts.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from app.core.config import settings


def test_connection():
    """Test database connection with current settings."""
    print("=" * 60)
    print("Database Connection Test")
    print("=" * 60)
    print(f"\nAttempting to connect to: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'database'}")
    print("(Password is hidden for security)\n")
    
    try:
        # Create engine
        engine = create_engine(settings.DATABASE_URL)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print("[SUCCESS] Connection successful!")
            print(f"\nPostgreSQL Version: {version}\n")
            
            # Check if database exists and list tables
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                print(f"[INFO] Found {len(tables)} table(s):")
                for table in tables:
                    print(f"   - {table}")
            else:
                print("[INFO] No tables found. Run 'python scripts/init_db.py' to create tables.")
            
            return True
            
    except Exception as e:
        print("[ERROR] Connection failed!")
        print(f"\nError: {str(e)}\n")
        print("=" * 60)
        print("TROUBLESHOOTING:")
        print("=" * 60)
        print("\n1. Check your .env file has correct DATABASE_URL")
        print("   Format: postgresql://USERNAME:PASSWORD@HOST:PORT/DATABASE_NAME")
        print("\n2. Verify PostgreSQL is running:")
        print("   - Check Windows Services for PostgreSQL")
        print("   - Or run: Get-Service -Name '*postgres*'")
        print("\n3. Test connection manually:")
        print("   psql -U postgres -d pps_db")
        print("\n4. Create database if it doesn't exist:")
        print("   psql -U postgres -c 'CREATE DATABASE pps_db;'")
        print("\n5. Common issues:")
        print("   - Wrong password")
        print("   - Database doesn't exist")
        print("   - PostgreSQL service not running")
        print("   - Wrong port (default is 5432)")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
