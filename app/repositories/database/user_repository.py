"""
User repository for database operations.
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.user import User


class UserRepository:
    """Repository for User model database operations."""
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID to search for
            
        Returns:
            User object if found, None otherwise
        """
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: Email address to search for
            
        Returns:
            User object if found, None otherwise
        """
        return self.db.query(User).filter(User.email == email).first()
    
    def create(self, email: str, hashed_password: str) -> User:
        """
        Create a new user.
        
        Args:
            email: User email address
            hashed_password: Bcrypt hashed password
            
        Returns:
            Created User object
            
        Raises:
            ValueError: If email already exists or other validation error
        """
        user = User(email=email, hashed_password=hashed_password)
        self.db.add(user)
        try:
            self.db.commit()
            self.db.refresh(user)
        except IntegrityError as e:
            # Likely duplicate email (unique constraint)
            self.db.rollback()
            raise ValueError("Email already exists") from e
        except Exception as e:
            # Rollback on any other database error
            self.db.rollback()
            raise ValueError(f"Database error: {str(e)}") from e
        return user
