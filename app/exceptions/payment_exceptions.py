"""
Custom exceptions for payment processing operations.
"""


class PaymentException(Exception):
    """Base exception for payment errors."""
    pass


class PaymentNotFoundError(PaymentException):
    """Raised when a payment/order/transaction is not found."""
    pass


class InvalidTransactionStateError(PaymentException):
    """Raised when a transaction operation is invalid for current state."""
    pass


class GatewayError(PaymentException):
    """Raised when payment gateway returns an error."""
    pass


class PaymentDeclinedError(PaymentException):
    """Raised when payment is declined by gateway."""
    pass


class InvalidCardError(PaymentException):
    """Raised when card details are invalid."""
    pass
