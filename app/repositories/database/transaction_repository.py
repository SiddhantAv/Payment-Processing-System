"""
Transaction repository for database operations.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.order import Order


class TransactionRepository:
    """Repository for Transaction model database operations."""
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """
        Get transaction by ID.
        
        Args:
            transaction_id: Transaction ID to search for
            
        Returns:
            Transaction object if found, None otherwise
        """
        return self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    def get_by_order_id(self, order_id: int) -> List[Transaction]:
        """
        Get all transactions for an order.
        
        Args:
            order_id: Order ID to search for
            
        Returns:
            List of Transaction objects
        """
        return self.db.query(Transaction).filter(Transaction.order_id == order_id).all()
    
    def get_by_gateway_transaction_id(self, gateway_transaction_id: str) -> Optional[Transaction]:
        """
        Get transaction by gateway transaction ID.
        
        Args:
            gateway_transaction_id: Gateway transaction ID to search for
            
        Returns:
            Transaction object if found, None otherwise
        """
        return self.db.query(Transaction).filter(
            Transaction.gateway_transaction_id == gateway_transaction_id
        ).first()
    
    def create(
        self,
        order_id: int,
        transaction_type: str,
        amount: float,
        status: str = "INITIATED",
        gateway_transaction_id: Optional[str] = None
    ) -> Transaction:
        """
        Create a new transaction.
        
        Args:
            order_id: Order ID this transaction belongs to
            transaction_type: Transaction type (PURCHASE, AUTHORIZE, etc.)
            amount: Transaction amount
            status: Transaction status (default: "INITIATED")
            gateway_transaction_id: Gateway transaction ID if available
            
        Returns:
            Created Transaction object
        """
        transaction = Transaction(
            order_id=order_id,
            type=transaction_type,
            amount=amount,
            status=status,
            gateway_transaction_id=gateway_transaction_id
        )
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction
    
    def update_status(self, transaction_id: int, status: str) -> Optional[Transaction]:
        """
        Update transaction status.
        
        Args:
            transaction_id: Transaction ID to update
            status: New status value
            
        Returns:
            Updated Transaction object if found, None otherwise
        """
        transaction = self.get_by_id(transaction_id)
        if transaction:
            transaction.status = status
            self.db.commit()
            self.db.refresh(transaction)
        return transaction
