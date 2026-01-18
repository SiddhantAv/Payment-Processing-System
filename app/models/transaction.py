"""
Transaction model for payment processing.
Represents individual payment transactions (purchase, authorize, capture, void, refund).
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Transaction(Base):
    """
    Transaction model representing a payment transaction.
    
    Each transaction is linked to an order and represents a specific payment operation.
    
    Attributes:
        id: Primary key (integer)
        order_id: Foreign key to orders table
        gateway_transaction_id: Transaction ID returned by payment gateway (Authorize.Net)
        type: Transaction type (PURCHASE, AUTHORIZE, CAPTURE, VOID, REFUND)
        status: Transaction status (INITIATED, SUCCESS, FAILED)
        amount: Transaction amount (decimal with precision)
        created_at: Timestamp when transaction was created
        order: Relationship to Order model (many-to-one)
    """
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    gateway_transaction_id = Column(String(255), nullable=True, index=True)
    type = Column(String(50), nullable=False, index=True)  # PURCHASE, AUTHORIZE, CAPTURE, VOID, REFUND
    status = Column(String(50), nullable=False, default="INITIATED", index=True)  # INITIATED, SUCCESS, FAILED
    amount = Column(Numeric(precision=10, scale=2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationship to order
    order = relationship(
        "Order",
        back_populates="transactions"
    )
