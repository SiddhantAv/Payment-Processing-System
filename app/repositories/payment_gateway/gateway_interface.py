"""
Abstract interface for payment gateway integrations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal


class GatewayResult:
    """Result object returned by payment gateway operations."""
    
    def __init__(
        self,
        success: bool,
        transaction_id: Optional[str] = None,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        error_text: Optional[str] = None
    ):
        """
        Initialize gateway result.
        
        Args:
            success: Whether the operation was successful
            transaction_id: Gateway transaction ID if successful
            message: Success or error message
            error_code: Gateway error code if failed
            error_text: Gateway error text if failed
        """
        self.success = success
        self.transaction_id = transaction_id
        self.message = message
        self.error_code = error_code
        self.error_text = error_text


class PaymentGatewayInterface(ABC):
    """Abstract interface for payment gateway implementations."""
    
    @abstractmethod
    def charge_card(
        self,
        amount: Decimal,
        currency: str,
        card_number: str,
        expiry_month: int,
        expiry_year: int,
        cvv: str
    ) -> GatewayResult:
        """
        Charge a credit card (authorize + capture in one step).
        
        Args:
            amount: Transaction amount
            currency: Currency code (e.g., "USD")
            card_number: Credit card number
            expiry_month: Card expiration month (1-12)
            expiry_year: Card expiration year (4 digits)
            cvv: Card CVV code
            
        Returns:
            GatewayResult with transaction details
        """
        pass
