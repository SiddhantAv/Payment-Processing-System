"""
Authentication API routes.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger("app.api.routes.auth")
from app.core.config import settings
from app.db.session import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import LoginRequest, TokenResponse, RegisterRequest, RegisterResponse
from app.exceptions.auth_exceptions import InvalidCredentialsError

# Create router for auth endpoints
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(
    login_request: LoginRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    User login endpoint.
    
    Authenticates user with email and password, returns JWT access token.
    
    Args:
        login_request: Login credentials (email and password)
        db: Database session
        
    Returns:
        TokenResponse containing access_token and token_type
        
    Raises:
        HTTPException: 401 if credentials are invalid
    """
    auth_service = AuthService(db)
    
    try:
        token_data = auth_service.login(
            email=login_request.email,
            password=login_request.password
        )
        return TokenResponse(**token_data)
    except InvalidCredentialsError as e:
        # Handle authentication errors
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    register_request: RegisterRequest,
    db: Session = Depends(get_db)
) -> RegisterResponse:
    """
    User registration endpoint.

    Creates a new user account with email and password.

    Args:
        register_request: Registration request (email and password)
        db: Database session

    Returns:
        RegisterResponse with user details

    Raises:
        HTTPException:
            - 409 if email already exists
            - 400 if input is invalid
            - 500 for unexpected errors
    """
    auth_service = AuthService(db)

    try:
        user = auth_service.register_user(
            email=register_request.email,
            password=register_request.password
        )
        # Explicitly construct response - datetime will be serialized by FastAPI/Pydantic
        return RegisterResponse.model_validate({
            "id": user.id,
            "email": user.email,
            "created_at": user.created_at
        })
    except ValueError as e:
        logger.warning(f"Registration failed - email conflict: {register_request.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in register endpoint: {type(e).__name__}: {str(e)}", exc_info=True)
        # In debug mode, return the actual error message for troubleshooting
        error_detail = str(e) if settings.DEBUG else "An unexpected error occurred. Please try again later."
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )
