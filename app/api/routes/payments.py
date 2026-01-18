"""
Payment API routes.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger("app.api.routes.payments")
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.payment_service import PaymentService
from app.schemas.payment import (
    PurchaseRequest,
    PurchaseResponse,
    AuthorizeRequest,
    AuthorizeResponse,
    CaptureRequest,
    CaptureResponse,
    CancelRequest,
    CancelResponse,
    RefundRequest,
    RefundResponse,
    OrderSummaryResponse,
    OrderDetailResponse,
)
from app.exceptions.payment_exceptions import (
    InvalidCardError,
    PaymentDeclinedError,
    GatewayError,
    PaymentNotFoundError,
    InvalidTransactionStateError,
)

# Create router for payment endpoints
router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/orders", response_model=list[OrderSummaryResponse], status_code=status.HTTP_200_OK)
def list_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[OrderSummaryResponse]:
    """
    List orders with transactions for the authenticated user.

    Returns order summaries including transaction history.
    """
    payment_service = PaymentService(db)
    return payment_service.list_orders_with_transactions(current_user)


@router.get("/orders/{order_id}", response_model=OrderDetailResponse, status_code=status.HTTP_200_OK)
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> OrderDetailResponse:
    """
    Get order details including transaction history and flags.
    """
    payment_service = PaymentService(db)
    try:
        return payment_service.get_order_detail(current_user, order_id)
    except PaymentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/purchase", response_model=PurchaseResponse, status_code=status.HTTP_200_OK)
def purchase(
    purchase_request: PurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> PurchaseResponse:
    """
    Process a purchase payment (authorize + capture in one step).
    
    This endpoint:
    - Creates an order
    - Processes payment through Authorize.Net
    - Creates a transaction record
    - Updates order status
    
    Args:
        purchase_request: Purchase request with payment details
        current_user: Authenticated user (from JWT token)
        db: Database session
        
    Returns:
        PurchaseResponse with order and transaction details
        
    Raises:
        HTTPException: 
            - 400 if card details are invalid
            - 402 if payment is declined
            - 502 if gateway error occurs
            - 500 for unexpected errors
    """
    payment_service = PaymentService(db)
    
    try:
        result = payment_service.process_purchase(
            user=current_user,
            purchase_request=purchase_request
        )
        return PurchaseResponse(**result)
        
    except InvalidCardError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except PaymentDeclinedError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    
    except GatewayError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment gateway error: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in purchase endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )


@router.post("/authorize", response_model=AuthorizeResponse, status_code=status.HTTP_200_OK)
def authorize(
    authorize_request: AuthorizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> AuthorizeResponse:
    """
    Process an authorize-only payment (hold funds without capture).

    This endpoint:
    - Creates an order
    - Processes authorization through Authorize.Net
    - Creates a transaction record

    Args:
        authorize_request: Authorize request with payment details
        current_user: Authenticated user (from JWT token)
        db: Database session

    Returns:
        AuthorizeResponse with order and transaction details

    Raises:
        HTTPException:
            - 400 if card details are invalid
            - 402 if payment is declined
            - 502 if gateway error occurs
            - 500 for unexpected errors
    """
    payment_service = PaymentService(db)

    try:
        result = payment_service.process_authorize(
            user=current_user,
            authorize_request=authorize_request
        )
        return AuthorizeResponse(**result)

    except InvalidCardError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except PaymentDeclinedError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )

    except GatewayError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment gateway error: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Unexpected error in purchase endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )


@router.post("/capture", response_model=CaptureResponse, status_code=status.HTTP_200_OK)
def capture(
    capture_request: CaptureRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CaptureResponse:
    """
    Capture a previously authorized transaction.

    This endpoint:
    - Validates prior authorization
    - Captures funds via Authorize.Net
    - Creates a CAPTURE transaction record
    - Updates order status on success

    Args:
        capture_request: Capture request with order_id and amount
        current_user: Authenticated user (from JWT token)
        db: Database session

    Returns:
        CaptureResponse with order and transaction details

    Raises:
        HTTPException:
            - 400 if no authorization found
            - 409 if already captured
            - 502 if gateway error occurs
            - 500 for unexpected errors
    """
    payment_service = PaymentService(db)

    try:
        result = payment_service.process_capture(
            user=current_user,
            capture_request=capture_request
        )
        return CaptureResponse(**result)

    except PaymentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except InvalidTransactionStateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

    except GatewayError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment gateway error: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Unexpected error in purchase endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )


@router.post("/cancel", response_model=CancelResponse, status_code=status.HTTP_200_OK)
def cancel(
    cancel_request: CancelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CancelResponse:
    """
    Void a previously authorized transaction (before capture).

    This endpoint:
    - Validates prior authorization
    - Ensures no capture exists
    - Voids the authorization via Authorize.Net
    - Creates a VOID transaction record
    - Updates order status to CANCELLED on success

    Args:
        cancel_request: Cancel request with order_id
        current_user: Authenticated user (from JWT token)
        db: Database session

    Returns:
        CancelResponse with order and transaction details

    Raises:
        HTTPException:
            - 400 if no authorization found
            - 409 if already captured
            - 502 if gateway error occurs
            - 500 for unexpected errors
    """
    payment_service = PaymentService(db)

    try:
        result = payment_service.process_cancel(
            user=current_user,
            cancel_request=cancel_request
        )
        return CancelResponse(**result)

    except PaymentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except InvalidTransactionStateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

    except GatewayError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment gateway error: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Unexpected error in purchase endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )


@router.post("/refund", response_model=RefundResponse, status_code=status.HTTP_200_OK)
def refund(
    refund_request: RefundRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> RefundResponse:
    """
    Refund a previously captured transaction (full or partial).

    This endpoint:
    - Validates prior capture
    - Validates refund amount
    - Creates a REFUND transaction record
    - Updates order status to REFUNDED on full refund

    ⚠️ **Important**: In Authorize.Net sandbox, transactions must be settled before refunds.
    Settlement typically occurs within 24 hours. If you get a "transaction does not meet criteria"
    error, wait a few minutes and try again, or wait until the next settlement batch.

    Args:
        refund_request: Refund request with order_id, amount, last_four, expiry
        current_user: Authenticated user (from JWT token)
        db: Database session

    Returns:
        RefundResponse with order and transaction details

    Raises:
        HTTPException:
            - 400 if no capture found or refund exceeds captured amount
            - 502 if gateway error occurs (may indicate transaction not settled yet)
            - 500 for unexpected errors
    """
    payment_service = PaymentService(db)

    try:
        result = payment_service.process_refund(
            user=current_user,
            refund_request=refund_request
        )
        return RefundResponse(**result)

    except PaymentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except InvalidTransactionStateError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except GatewayError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment gateway error: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Unexpected error in purchase endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )
