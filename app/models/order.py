"""
Order model for payment processing.
Represents a customer order that can have multiple payment transactions.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Order(Base):
    """
    Order model representing a customer order.
    
    An order can have multiple transactions (authorize, capture, refund, etc.)
    
    Attributes:
        id: Primary key (integer)
        user_id: Foreign key to users table
        amount: Order amount (decimal with precision)
        currency: Currency code (e.g., "USD")
        status: Order status (e.g., "pending", "completed", "cancelled")
        created_at: Timestamp when order was created
        updated_at: Timestamp when order was last updated
        transactions: Relationship to Transaction model (one-to-many)
    """
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(precision=10, scale=2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(String(50), nullable=False, default="pending", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationship to transactions
    transactions = relationship(
        "Transaction",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
