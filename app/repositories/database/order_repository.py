"""
Order repository for database operations.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.order import Order
from app.models.user import User


class OrderRepository:
    """Repository for Order model database operations."""
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def get_by_id(self, order_id: int) -> Optional[Order]:
        """
        Get order by ID.
        
        Args:
            order_id: Order ID to search for
            
        Returns:
            Order object if found, None otherwise
        """
        return self.db.query(Order).filter(Order.id == order_id).first()
    
    def get_by_user_id(self, user_id: int) -> List[Order]:
        """
        Get all orders for a user.
        
        Args:
            user_id: User ID to search for
            
        Returns:
            List of Order objects
        """
        return self.db.query(Order).filter(Order.user_id == user_id).all()

    def get_by_id_and_user_id(self, order_id: int, user_id: int) -> Optional[Order]:
        """
        Get order by ID scoped to a specific user.

        Args:
            order_id: Order ID to search for
            user_id: User ID to scope the search

        Returns:
            Order object if found and owned by user, None otherwise
        """
        return (
            self.db.query(Order)
            .filter(Order.id == order_id, Order.user_id == user_id)
            .first()
        )
    
    def create(
        self,
        user_id: int,
        amount: float,
        currency: str = "USD",
        status: str = "pending"
    ) -> Order:
        """
        Create a new order.
        
        Args:
            user_id: User ID who owns the order
            amount: Order amount
            currency: Currency code (default: "USD")
            status: Order status (default: "pending")
            
        Returns:
            Created Order object
        """
        order = Order(
            user_id=user_id,
            amount=amount,
            currency=currency,
            status=status
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order
    
    def update_status(self, order_id: int, status: str) -> Optional[Order]:
        """
        Update order status.
        
        Args:
            order_id: Order ID to update
            status: New status value
            
        Returns:
            Updated Order object if found, None otherwise
        """
        order = self.get_by_id(order_id)
        if order:
            order.status = status
            self.db.commit()
            self.db.refresh(order)
        return order
