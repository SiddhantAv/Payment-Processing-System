"""
Pydantic schemas for payment endpoints.
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from decimal import Decimal
from typing import Optional


class PurchaseRequest(BaseModel):
    """Schema for purchase payment request."""
    
    amount: Decimal = Field(..., gt=0, description="Transaction amount (must be greater than 0)")
    currency: str = Field(default="USD", max_length=3, description="Currency code (e.g., USD)")
    card_number: str = Field(
        ...,
        min_length=13,
        max_length=19,
        description="Credit card number (13-19 digits). Spaces and dashes are automatically removed. Must contain only numeric digits."
    )
    expiry_month: int = Field(..., ge=1, le=12, description="Card expiration month (1-12)")
    expiry_year: int = Field(..., ge=2024, le=2099, description="Card expiration year (4 digits)")
    cvv: str = Field(..., min_length=3, max_length=4, description="Card CVV code")
    
    @field_validator('card_number')
    @classmethod
    def validate_card_number(cls, v: str) -> str:
        """
        Validate and normalize card number.
        
        Rules:
        - Removes spaces and dashes for formatting
        - Must contain only numeric digits (0-9)
        - Length must be between 13 and 19 digits after normalization
        - Card number format is validated by the payment gateway
        
        Note: The payment gateway (Authorize.Net) will perform additional validation
        including Luhn algorithm check and card brand verification.
        """
        # Remove spaces and dashes
        normalized = v.replace(" ", "").replace("-", "")
        
        # Validate that it contains only digits
        if not normalized.isdigit():
            raise ValueError("Card number must contain only numeric digits (0-9)")
        
        # Validate length after normalization
        if len(normalized) < 13 or len(normalized) > 19:
            raise ValueError("Card number must be between 13 and 19 digits")
        
        return normalized
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": "100.00",
                "currency": "USD",
                "card_number": "4111111111111111",
                "expiry_month": 12,
                "expiry_year": 2026,
                "cvv": "123"
            }
        }


class PurchaseResponse(BaseModel):
    """Schema for purchase payment response."""
    
    order_id: int = Field(..., description="Order ID")
    transaction_id: int = Field(..., description="Transaction ID")
    gateway_transaction_id: Optional[str] = Field(None, description="Gateway transaction ID")
    status: str = Field(..., description="Transaction status (SUCCESS or FAILED)")
    message: str = Field(..., description="Response message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "order_id": 1,
                "transaction_id": 1,
                "gateway_transaction_id": "1234567890",
                "status": "SUCCESS",
                "message": "Payment processed successfully"
            }
        }


class AuthorizeRequest(BaseModel):
    """Schema for authorize-only payment request."""

    amount: Decimal = Field(..., gt=0, description="Transaction amount (must be greater than 0)")
    currency: str = Field(default="USD", max_length=3, description="Currency code (e.g., USD)")
    card_number: str = Field(
        ...,
        min_length=13,
        max_length=19,
        description="Credit card number (13-19 digits). Spaces and dashes are automatically removed. Must contain only numeric digits."
    )
    expiry_month: int = Field(..., ge=1, le=12, description="Card expiration month (1-12)")
    expiry_year: int = Field(..., ge=2024, le=2099, description="Card expiration year (4 digits)")
    cvv: str = Field(..., min_length=3, max_length=4, description="Card CVV code")

    @field_validator('card_number')
    @classmethod
    def validate_card_number(cls, v: str) -> str:
        """
        Validate and normalize card number.
        
        Rules:
        - Removes spaces and dashes for formatting
        - Must contain only numeric digits (0-9)
        - Length must be between 13 and 19 digits after normalization
        - Card number format is validated by the payment gateway
        
        Note: The payment gateway (Authorize.Net) will perform additional validation
        including Luhn algorithm check and card brand verification.
        """
        # Remove spaces and dashes
        normalized = v.replace(" ", "").replace("-", "")
        
        # Validate that it contains only digits
        if not normalized.isdigit():
            raise ValueError("Card number must contain only numeric digits (0-9)")
        
        # Validate length after normalization
        if len(normalized) < 13 or len(normalized) > 19:
            raise ValueError("Card number must be between 13 and 19 digits")
        
        return normalized

    class Config:
        json_schema_extra = {
            "example": {
                "amount": "100.00",
                "currency": "USD",
                "card_number": "4111111111111111",
                "expiry_month": 12,
                "expiry_year": 2026,
                "cvv": "123"
            }
        }


class AuthorizeResponse(BaseModel):
    """Schema for authorize-only payment response."""

    order_id: int = Field(..., description="Order ID")
    transaction_id: int = Field(..., description="Transaction ID")
    gateway_transaction_id: Optional[str] = Field(None, description="Gateway transaction ID")
    status: str = Field(..., description="Transaction status (SUCCESS or FAILED)")
    message: str = Field(..., description="Response message")

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": 1,
                "transaction_id": 1,
                "gateway_transaction_id": "1234567890",
                "status": "SUCCESS",
                "message": "Authorization successful"
            }
        }


class CaptureRequest(BaseModel):
    """Schema for capture payment request."""

    order_id: int = Field(..., gt=0, description="Order ID to capture")
    amount: Decimal = Field(..., gt=0, description="Capture amount (must be greater than 0)")

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": 1,
                "amount": "100.00"
            }
        }


class CaptureResponse(BaseModel):
    """Schema for capture payment response."""

    order_id: int = Field(..., description="Order ID")
    transaction_id: int = Field(..., description="Transaction ID")
    gateway_transaction_id: Optional[str] = Field(None, description="Gateway transaction ID")
    status: str = Field(..., description="Transaction status (SUCCESS or FAILED)")
    message: str = Field(..., description="Response message")

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": 1,
                "transaction_id": 2,
                "gateway_transaction_id": "0987654321",
                "status": "SUCCESS",
                "message": "Capture successful"
            }
        }


class CancelRequest(BaseModel):
    """Schema for cancel/void payment request."""

    order_id: int = Field(..., gt=0, description="Order ID to void")

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": 1
            }
        }


class CancelResponse(BaseModel):
    """Schema for cancel/void payment response."""

    order_id: int = Field(..., description="Order ID")
    transaction_id: int = Field(..., description="Transaction ID")
    gateway_transaction_id: Optional[str] = Field(None, description="Gateway transaction ID")
    status: str = Field(..., description="Transaction status (SUCCESS or FAILED)")
    message: str = Field(..., description="Response message")

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": 1,
                "transaction_id": 3,
                "gateway_transaction_id": "1122334455",
                "status": "SUCCESS",
                "message": "Void successful"
            }
        }


class RefundRequest(BaseModel):
    """Schema for refund payment request."""

    order_id: int = Field(..., gt=0, description="Order ID to refund")
    amount: Decimal = Field(..., gt=0, description="Refund amount (must be greater than 0)")
    last_four: str = Field(..., min_length=4, max_length=4, description="Last 4 digits of card")
    expiry_month: int = Field(..., ge=1, le=12, description="Card expiration month (1-12)")
    expiry_year: int = Field(..., ge=2000, le=2099, description="Card expiration year (4 digits)")

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": 1,
                "amount": "10.00",
                "last_four": "1111",
                "expiry_month": 12,
                "expiry_year": 2026
            }
        }


class RefundResponse(BaseModel):
    """Schema for refund payment response."""

    order_id: int = Field(..., description="Order ID")
    transaction_id: int = Field(..., description="Transaction ID")
    gateway_transaction_id: Optional[str] = Field(None, description="Gateway transaction ID")
    status: str = Field(..., description="Transaction status (SUCCESS or FAILED)")
    message: str = Field(..., description="Response message")

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": 1,
                "transaction_id": 4,
                "gateway_transaction_id": "5566778899",
                "status": "SUCCESS",
                "message": "Refund successful"
            }
        }


class TransactionSummary(BaseModel):
    """Schema for transaction summary in order responses."""

    transaction_id: int = Field(..., description="Transaction ID")
    type: str = Field(..., description="Transaction type")
    status: str = Field(..., description="Transaction status")
    amount: Decimal = Field(..., description="Transaction amount")
    gateway_transaction_id: Optional[str] = Field(None, description="Gateway transaction ID")
    created_at: datetime = Field(..., description="Transaction creation timestamp")


class OrderSummaryResponse(BaseModel):
    """Schema for order summary with transactions list."""

    order_id: int = Field(..., description="Order ID")
    order_status: str = Field(..., description="Order status")
    amount: Decimal = Field(..., description="Order amount")
    currency: str = Field(..., description="Order currency")
    created_at: datetime = Field(..., description="Order creation timestamp")
    transactions: list[TransactionSummary] = Field(..., description="Transactions for this order")


class OrderDetailResponse(BaseModel):
    """Schema for detailed order response."""

    order_id: int = Field(..., description="Order ID")
    order_status: str = Field(..., description="Order status")
    amount: Decimal = Field(..., description="Order amount")
    currency: str = Field(..., description="Order currency")
    created_at: datetime = Field(..., description="Order creation timestamp")
    transactions: list[TransactionSummary] = Field(..., description="Full transaction history")
    last_successful_transaction: Optional[TransactionSummary] = Field(
        None,
        description="Most recent successful transaction"
    )
    refundable_amount: Decimal = Field(..., description="Remaining refundable amount")
    can_capture: bool = Field(..., description="Whether a capture is allowed")
    can_cancel: bool = Field(..., description="Whether a cancel/void is allowed")
    can_refund: bool = Field(..., description="Whether a refund is allowed")
