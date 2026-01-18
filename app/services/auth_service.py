"""
Authentication service for user authentication and JWT token management.
"""
import logging
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger("app.services.auth_service")
from app.repositories.database.user_repository import UserRepository
from app.core.security import verify_password, create_access_token, hash_password
from app.models.user import User
from app.exceptions.auth_exceptions import InvalidCredentialsError


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self, db: Session):
        """
        Initialize auth service with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.user_repository = UserRepository(db)
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user by email and password.
        
        Args:
            email: User email address
            password: Plain text password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        user = self.user_repository.get_by_email(email)
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return user
    
    def login(self, email: str, password: str) -> dict:
        """
        Perform user login and return JWT token.
        
        Args:
            email: User email address
            password: Plain text password
            
        Returns:
            Dictionary containing access_token and token_type
            
        Raises:
            InvalidCredentialsError: If email or password is incorrect
        """
        user = self.authenticate_user(email, password)
        
        if not user:
            logger.warning(f"Failed login attempt for email: {email}")
            raise InvalidCredentialsError("Invalid email or password")
        
        # Create JWT token with user ID
        access_token = create_access_token(data={"sub": str(user.id)})
        logger.info(f"User {user.id} ({email}) logged in successfully")
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    def register_user(self, email: str, password: str) -> User:
        """
        Register a new user.

        Args:
            email: User email address
            password: Plain text password

        Returns:
            Created User object

        Raises:
            ValueError: If email already exists
        """
        existing_user = self.user_repository.get_by_email(email)
        if existing_user:
            raise ValueError("Email already exists")

        hashed_password = hash_password(password)
        return self.user_repository.create(email=email, hashed_password=hashed_password)
