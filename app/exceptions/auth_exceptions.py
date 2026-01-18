"""
Custom exceptions for authentication operations.
"""


class AuthException(Exception):
    """Base exception for authentication errors."""
    pass


class InvalidCredentialsError(AuthException):
    """Raised when user credentials are invalid."""
    pass


class TokenExpiredError(AuthException):
    """Raised when JWT token has expired."""
    pass


class TokenInvalidError(AuthException):
    """Raised when JWT token is invalid or malformed."""
    pass
