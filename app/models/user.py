"""
User model for authentication.
"""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class User(Base):
    """
    User model representing authenticated users.
    
    Attributes:
        id: Primary key (integer)
        email: Unique email address
        hashed_password: Bcrypt hashed password
        created_at: Timestamp when user was created
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
