"""
Payment service for processing payment transactions.
"""
import logging
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.user import User

logger = logging.getLogger("app.services.payment_service")
from app.repositories.database.order_repository import OrderRepository
from app.repositories.database.transaction_repository import TransactionRepository
from app.repositories.payment_gateway.authorize_net_repository import AuthorizeNetRepository
from app.repositories.payment_gateway.gateway_interface import GatewayResult
from app.schemas.payment import (
    PurchaseRequest,
    AuthorizeRequest,
    CaptureRequest,
    CancelRequest,
    RefundRequest,
    TransactionSummary,
    OrderSummaryResponse,
    OrderDetailResponse,
)
from app.exceptions.payment_exceptions import (
    GatewayError,
    PaymentDeclinedError,
    InvalidCardError,
    PaymentNotFoundError,
    InvalidTransactionStateError,
)


class PaymentService:
    """Service for payment processing operations."""
    
    def __init__(self, db: Session):
        """
        Initialize payment service with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.order_repository = OrderRepository(db)
        self.transaction_repository = TransactionRepository(db)
        self.gateway_repository = AuthorizeNetRepository()
    
    def process_purchase(
        self,
        user: User,
        purchase_request: PurchaseRequest
    ) -> dict:
        """
        Process a purchase payment (authorize + capture in one step).
        
        Creates an order, processes payment through gateway, creates transaction,
        and updates order status.
        
        Note: Each repository operation commits individually. If gateway succeeds
        but database operations fail afterward, an error is logged and raised.
        The order will remain in PENDING state for manual review.
        
        Args:
            user: Authenticated user making the purchase
            purchase_request: Purchase request with payment details
            
        Returns:
            Dictionary with order_id, transaction_id, gateway_transaction_id, status, message
            
        Raises:
            InvalidCardError: If card details are invalid
            PaymentDeclinedError: If payment is declined
            GatewayError: If gateway returns an error
        """
        logger.info(f"Processing purchase for user {user.id}, amount {purchase_request.amount} {purchase_request.currency}")
        
        # Create order with PENDING status
        order = self.order_repository.create(
            user_id=user.id,
            amount=float(purchase_request.amount),
            currency=purchase_request.currency,
            status="PENDING"
        )
        logger.debug(f"Created order {order.id} with status PENDING")
        
        try:
            # Process payment through gateway
            gateway_result: GatewayResult = self.gateway_repository.charge_card(
                amount=purchase_request.amount,
                currency=purchase_request.currency,
                card_number=purchase_request.card_number,
                expiry_month=purchase_request.expiry_month,
                expiry_year=purchase_request.expiry_year,
                cvv=purchase_request.cvv
            )
            logger.info(f"Gateway charge successful for order {order.id}, transaction_id: {gateway_result.transaction_id}")
            
            # Create transaction record and update order status within transaction context
            try:
                # Create transaction record
                transaction = self.transaction_repository.create(
                    order_id=order.id,
                    transaction_type="PURCHASE",
                    amount=float(purchase_request.amount),
                    status="SUCCESS",
                    gateway_transaction_id=gateway_result.transaction_id
                )
                
                # Update order status to COMPLETED
                self.order_repository.update_status(order.id, "COMPLETED")
                logger.info(f"Purchase completed successfully for order {order.id}")
                
                return {
                    "order_id": order.id,
                    "transaction_id": transaction.id,
                    "gateway_transaction_id": gateway_result.transaction_id,
                    "status": "SUCCESS",
                    "message": f"Purchase completed successfully. Amount {purchase_request.amount} {purchase_request.currency} has been charged."
                }
            except Exception as db_error:
                # Database operation failed after gateway success - log critical error
                logger.error(f"Database error after successful gateway charge for order {order.id}: {str(db_error)}", exc_info=True)
                # Re-raise to be handled by outer exception handler
                raise GatewayError(f"Payment processed but failed to record transaction: {str(db_error)}") from db_error
            
        except (InvalidCardError, PaymentDeclinedError) as e:
            # Payment declined or invalid card
            logger.warning(f"Payment declined for order {order.id}: {str(e)}")
            # Create failed transaction record
            transaction = self.transaction_repository.create(
                order_id=order.id,
                transaction_type="PURCHASE",
                amount=float(purchase_request.amount),
                status="FAILED",
                gateway_transaction_id=None
            )
            
            # Update order status to FAILED
            self.order_repository.update_status(order.id, "FAILED")
            
            # Re-raise the exception for API layer to handle
            raise
        except GatewayError as e:
            logger.error(f"Gateway error during purchase for order {order.id}: {str(e)}", exc_info=True)
            raise

    def process_authorize(
        self,
        user: User,
        authorize_request: AuthorizeRequest
    ) -> dict:
        """
        Process an authorize-only payment (hold funds without capture).

        Creates an order, processes authorization through gateway, creates transaction,
        and updates order status on failure.

        Args:
            user: Authenticated user making the authorization
            authorize_request: Authorize request with payment details

        Returns:
            Dictionary with order_id, transaction_id, gateway_transaction_id, status, message

        Raises:
            InvalidCardError: If card details are invalid
            PaymentDeclinedError: If payment is declined
            GatewayError: If gateway returns an error
        """
        # Create order with PENDING status
        order = self.order_repository.create(
            user_id=user.id,
            amount=float(authorize_request.amount),
            currency=authorize_request.currency,
            status="PENDING"
        )

        try:
            # Process authorization through gateway
            gateway_result: GatewayResult = self.gateway_repository.authorize_card(
                amount=authorize_request.amount,
                currency=authorize_request.currency,
                card_number=authorize_request.card_number,
                expiry_month=authorize_request.expiry_month,
                expiry_year=authorize_request.expiry_year,
                cvv=authorize_request.cvv
            )

            # Create transaction record
            transaction = self.transaction_repository.create(
                order_id=order.id,
                transaction_type="AUTHORIZE",
                amount=float(authorize_request.amount),
                status="SUCCESS",
                gateway_transaction_id=gateway_result.transaction_id
            )

            return {
                "order_id": order.id,
                "transaction_id": transaction.id,
                "gateway_transaction_id": gateway_result.transaction_id,
                "status": "SUCCESS",
                "message": gateway_result.message or "Authorization successful"
            }

        except (InvalidCardError, PaymentDeclinedError):
            # Create failed transaction record
            transaction = self.transaction_repository.create(
                order_id=order.id,
                transaction_type="AUTHORIZE",
                amount=float(authorize_request.amount),
                status="FAILED",
                gateway_transaction_id=None
            )

            # Update order status to FAILED
            self.order_repository.update_status(order.id, "FAILED")

            # Re-raise the exception for API layer to handle
            raise

        except GatewayError:
            # Create failed transaction record
            transaction = self.transaction_repository.create(
                order_id=order.id,
                transaction_type="AUTHORIZE",
                amount=float(authorize_request.amount),
                status="FAILED",
                gateway_transaction_id=None
            )

            # Update order status to FAILED
            self.order_repository.update_status(order.id, "FAILED")

            # Re-raise the exception for API layer to handle
            raise

    def process_capture(
        self,
        user: User,
        capture_request: CaptureRequest
    ) -> dict:
        """
        Process a capture payment for a previously authorized transaction.

        Validates that a successful authorization exists and capture has not already occurred.

        Args:
            user: Authenticated user making the capture request
            capture_request: Capture request with order_id and amount

        Returns:
            Dictionary with order_id, transaction_id, gateway_transaction_id, status, message

        Raises:
            PaymentNotFoundError: If order or authorization is not found
            InvalidTransactionStateError: If already captured
            GatewayError: If gateway returns an error
        """
        order = self.order_repository.get_by_id(capture_request.order_id)
        if not order or order.user_id != user.id:
            raise PaymentNotFoundError("Order not found")

        # Find successful authorization transaction
        transactions = self.transaction_repository.get_by_order_id(order.id)
        authorized_transactions = [
            t for t in transactions
            if t.type == "AUTHORIZE" and t.status == "SUCCESS" and t.gateway_transaction_id
        ]

        if not authorized_transactions:
            raise PaymentNotFoundError("No successful authorization found for this order")

        # Check if already captured
        captured_transactions = [
            t for t in transactions
            if t.type == "CAPTURE" and t.status == "SUCCESS"
        ]
        if captured_transactions:
            raise InvalidTransactionStateError("Order already captured")

        # Use the most recent successful authorization
        authorized_transactions.sort(key=lambda t: t.id, reverse=True)
        authorization = authorized_transactions[0]

        try:
            gateway_result: GatewayResult = self.gateway_repository.capture_transaction(
                gateway_transaction_id=authorization.gateway_transaction_id,
                amount=capture_request.amount
            )

            # Create capture transaction record
            transaction = self.transaction_repository.create(
                order_id=order.id,
                transaction_type="CAPTURE",
                amount=float(capture_request.amount),
                status="SUCCESS",
                gateway_transaction_id=gateway_result.transaction_id
            )

            # Update order status to COMPLETED
            self.order_repository.update_status(order.id, "COMPLETED")

            return {
                "order_id": order.id,
                "transaction_id": transaction.id,
                "gateway_transaction_id": gateway_result.transaction_id,
                "status": "SUCCESS",
                "message": gateway_result.message or "Capture successful"
            }

        except GatewayError:
            # Create failed capture transaction record
            transaction = self.transaction_repository.create(
                order_id=order.id,
                transaction_type="CAPTURE",
                amount=float(capture_request.amount),
                status="FAILED",
                gateway_transaction_id=None
            )

            # Update order status to FAILED
            self.order_repository.update_status(order.id, "FAILED")

            # Re-raise the exception for API layer to handle
            raise

    def process_cancel(
        self,
        user: User,
        cancel_request: CancelRequest
    ) -> dict:
        """
        Void a previously authorized transaction (before capture).

        Validates that a successful authorization exists and capture has not occurred.

        Args:
            user: Authenticated user making the cancel request
            cancel_request: Cancel request with order_id

        Returns:
            Dictionary with order_id, transaction_id, gateway_transaction_id, status, message

        Raises:
            PaymentNotFoundError: If order or authorization is not found
            InvalidTransactionStateError: If already captured
            GatewayError: If gateway returns an error
        """
        order = self.order_repository.get_by_id(cancel_request.order_id)
        if not order or order.user_id != user.id:
            raise PaymentNotFoundError("Order not found")

        transactions = self.transaction_repository.get_by_order_id(order.id)

        authorized_transactions = [
            t for t in transactions
            if t.type == "AUTHORIZE" and t.status == "SUCCESS" and t.gateway_transaction_id
        ]

        if not authorized_transactions:
            raise PaymentNotFoundError("No successful authorization found for this order")

        captured_transactions = [
            t for t in transactions
            if t.type == "CAPTURE" and t.status == "SUCCESS"
        ]
        if captured_transactions:
            raise InvalidTransactionStateError("Order already captured")

        # Use the most recent successful authorization
        authorized_transactions.sort(key=lambda t: t.id, reverse=True)
        authorization = authorized_transactions[0]

        try:
            gateway_result: GatewayResult = self.gateway_repository.void_transaction(
                gateway_transaction_id=authorization.gateway_transaction_id
            )

            transaction = self.transaction_repository.create(
                order_id=order.id,
                transaction_type="VOID",
                amount=float(authorization.amount),
                status="SUCCESS",
                gateway_transaction_id=gateway_result.transaction_id
            )

            # Update order status to CANCELLED
            self.order_repository.update_status(order.id, "CANCELLED")

            return {
                "order_id": order.id,
                "transaction_id": transaction.id,
                "gateway_transaction_id": gateway_result.transaction_id,
                "status": "SUCCESS",
                "message": "Authorization cancelled successfully"
            }

        except GatewayError:
            transaction = self.transaction_repository.create(
                order_id=order.id,
                transaction_type="VOID",
                amount=float(authorization.amount),
                status="FAILED",
                gateway_transaction_id=None
            )

            # Keep order status as PENDING on failure
            raise

    def process_refund(
        self,
        user: User,
        refund_request: RefundRequest
    ) -> dict:
        """
        Process a refund for a previously captured transaction.

        Supports full and partial refunds. Requires successful capture.

        Args:
            user: Authenticated user making the refund request
            refund_request: Refund request with order_id and amount

        Returns:
            Dictionary with order_id, transaction_id, gateway_transaction_id, status, message

        Raises:
            PaymentNotFoundError: If order or capture is not found
            InvalidTransactionStateError: If refund exceeds captured amount
            GatewayError: If gateway returns an error
        """
        order = self.order_repository.get_by_id(refund_request.order_id)
        if not order or order.user_id != user.id:
            raise PaymentNotFoundError("Order not found")

        transactions = self.transaction_repository.get_by_order_id(order.id)

        # Find captured transactions (both CAPTURE and PURCHASE are refundable)
        # PURCHASE = authorize + capture in one step, so it's also refundable
        captured_transactions = [
            t for t in transactions
            if t.type in ("CAPTURE", "PURCHASE") and t.status == "SUCCESS" and t.gateway_transaction_id
        ]

        if not captured_transactions:
            raise PaymentNotFoundError("No successful capture or purchase found for this order")

        total_captured = sum(Decimal(str(t.amount)) for t in captured_transactions)
        total_refunded = sum(
            Decimal(str(t.amount)) for t in transactions
            if t.type == "REFUND" and t.status == "SUCCESS"
        )

        refund_amount = Decimal(str(refund_request.amount))
        remaining = total_captured - total_refunded

        if refund_amount > remaining:
            raise InvalidTransactionStateError("Refund amount exceeds captured amount")

        # Determine which transaction ID to use for refund
        # For PURCHASE transactions: use the PURCHASE transaction ID
        # For AUTHORIZE + CAPTURE flow: Try both capture ID and authorization ID
        # Authorize.Net behavior varies - some require capture ID, others require auth ID
        captured_transactions.sort(key=lambda t: t.id, reverse=True)
        capture_txn = captured_transactions[0]
        
        # Get authorization transaction ID as fallback
        authorize_transactions = [
            t for t in transactions
            if t.type == "AUTHORIZE" and t.status == "SUCCESS" and t.gateway_transaction_id
        ]
        auth_transaction_id = None
        if authorize_transactions:
            authorize_transactions.sort(key=lambda t: t.id, reverse=True)
            auth_transaction_id = authorize_transactions[0].gateway_transaction_id
        
        # Try capture transaction ID first (most common case)
        refund_transaction_id = capture_txn.gateway_transaction_id
        if not refund_transaction_id:
            raise PaymentNotFoundError("Capture transaction missing gateway transaction ID")

        try:
            gateway_result: GatewayResult = self.gateway_repository.refund_transaction(
                gateway_transaction_id=refund_transaction_id,
                amount=refund_amount,
                last_four=refund_request.last_four,
                expiry_month=refund_request.expiry_month,
                expiry_year=refund_request.expiry_year
            )

            transaction = self.transaction_repository.create(
                order_id=order.id,
                transaction_type="REFUND",
                amount=float(refund_amount),
                status="SUCCESS",
                gateway_transaction_id=gateway_result.transaction_id
            )

            # Update order status on full refund
            if refund_amount == remaining:
                self.order_repository.update_status(order.id, "REFUNDED")

            return {
                "order_id": order.id,
                "transaction_id": transaction.id,
                "gateway_transaction_id": gateway_result.transaction_id,
                "status": "SUCCESS",
                "message": gateway_result.message or "Refund successful"
            }

        except GatewayError as e:
            # Check if error is about transaction not meeting criteria
            error_msg = str(e).lower()
            is_settlement_error = (
                "does not meet the criteria" in error_msg or
                "criteria for issuing" in error_msg
            )
            
            # If capture transaction ID failed and we have an authorization ID,
            # try using the authorization transaction ID instead
            # (Authorize.Net sometimes requires the original auth ID for refunds)
            if is_settlement_error and auth_transaction_id and auth_transaction_id != refund_transaction_id:
                # Try with authorization transaction ID
                try:
                    gateway_result: GatewayResult = self.gateway_repository.refund_transaction(
                        gateway_transaction_id=auth_transaction_id,
                        amount=refund_amount,
                        last_four=refund_request.last_four,
                        expiry_month=refund_request.expiry_month,
                        expiry_year=refund_request.expiry_year
                    )
                    
                    # Success with authorization ID - create refund transaction
                    transaction = self.transaction_repository.create(
                        order_id=order.id,
                        transaction_type="REFUND",
                        amount=float(refund_amount),
                        status="SUCCESS",
                        gateway_transaction_id=gateway_result.transaction_id
                    )
                    
                    # Update order status on full refund
                    if refund_amount == remaining:
                        self.order_repository.update_status(order.id, "REFUNDED")
                    
                    return {
                        "order_id": order.id,
                        "transaction_id": transaction.id,
                        "gateway_transaction_id": gateway_result.transaction_id,
                        "status": "SUCCESS",
                        "message": gateway_result.message or "Refund successful"
                    }
                except GatewayError as e2:
                    # Authorization ID also failed - create failed transaction and provide helpful error
                    transaction = self.transaction_repository.create(
                        order_id=order.id,
                        transaction_type="REFUND",
                        amount=float(refund_amount),
                        status="FAILED",
                        gateway_transaction_id=None
                    )
                    # Provide more helpful error message
                    error_msg = str(e2)
                    if "does not meet the criteria" in error_msg.lower():
                        raise GatewayError(
                            f"Refund failed: Transaction may not be settled yet. "
                            f"Authorize.Net requires transactions to be settled before refunds. "
                            f"Please wait a few minutes and try again, or wait until the next settlement batch. "
                            f"Tried transaction IDs: capture={refund_transaction_id}, auth={auth_transaction_id}"
                        )
                    raise e2
            else:
                # No fallback - create failed transaction and provide helpful error
                transaction = self.transaction_repository.create(
                    order_id=order.id,
                    transaction_type="REFUND",
                    amount=float(refund_amount),
                    status="FAILED",
                    gateway_transaction_id=None
                )
                # Provide more helpful error message
                error_msg = str(e)
                if "does not meet the criteria" in error_msg.lower():
                    raise GatewayError(
                        f"Refund failed: Transaction may not be settled yet. "
                        f"Authorize.Net requires transactions to be settled before refunds. "
                        f"Please wait a few minutes and try again, or wait until the next settlement batch. "
                        f"Used transaction ID: {refund_transaction_id}"
                    )
                raise e

    def list_orders_with_transactions(self, user: User) -> list[OrderSummaryResponse]:
        """
        List all orders for a user with their transactions.

        Args:
            user: Authenticated user

        Returns:
            List of OrderSummaryResponse objects
        """
        orders = self.order_repository.get_by_user_id(user.id)
        results: list[OrderSummaryResponse] = []

        for order in orders:
            transactions = self.transaction_repository.get_by_order_id(order.id)
            transaction_summaries = [
                TransactionSummary(
                    transaction_id=t.id,
                    type=t.type,
                    status=t.status,
                    amount=Decimal(str(t.amount)),
                    gateway_transaction_id=t.gateway_transaction_id,
                    created_at=t.created_at,
                )
                for t in transactions
            ]

            results.append(
                OrderSummaryResponse(
                    order_id=order.id,
                    order_status=order.status,
                    amount=Decimal(str(order.amount)),
                    currency=order.currency,
                    created_at=order.created_at,
                    transactions=transaction_summaries,
                )
            )

        return results

    def get_order_detail(self, user: User, order_id: int) -> OrderDetailResponse:
        """
        Get detailed order information with transaction history and flags.

        Args:
            user: Authenticated user
            order_id: Order ID to fetch

        Returns:
            OrderDetailResponse object

        Raises:
            PaymentNotFoundError: If order not found or not owned by user
        """
        order = self.order_repository.get_by_id_and_user_id(order_id, user.id)
        if not order:
            raise PaymentNotFoundError("Order not found")

        transactions = self.transaction_repository.get_by_order_id(order.id)
        transaction_summaries = [
            TransactionSummary(
                transaction_id=t.id,
                type=t.type,
                status=t.status,
                amount=Decimal(str(t.amount)),
                gateway_transaction_id=t.gateway_transaction_id,
                created_at=t.created_at,
            )
            for t in transactions
        ]

        successful_transactions = [
            t for t in transactions if t.status == "SUCCESS"
        ]
        successful_transactions.sort(key=lambda t: t.id, reverse=True)

        last_successful = None
        if successful_transactions:
            t = successful_transactions[0]
            last_successful = TransactionSummary(
                transaction_id=t.id,
                type=t.type,
                status=t.status,
                amount=Decimal(str(t.amount)),
                gateway_transaction_id=t.gateway_transaction_id,
                created_at=t.created_at,
            )

        captured_total = sum(
            Decimal(str(t.amount)) for t in transactions
            if t.type == "CAPTURE" and t.status == "SUCCESS"
        )
        refunded_total = sum(
            Decimal(str(t.amount)) for t in transactions
            if t.type == "REFUND" and t.status == "SUCCESS"
        )
        refundable_amount = captured_total - refunded_total
        if refundable_amount < Decimal("0"):
            refundable_amount = Decimal("0")

        has_success_authorize = any(
            t.type == "AUTHORIZE" and t.status == "SUCCESS" and t.gateway_transaction_id
            for t in transactions
        )
        has_success_capture = any(
            t.type == "CAPTURE" and t.status == "SUCCESS"
            for t in transactions
        )

        can_capture = has_success_authorize and not has_success_capture
        can_cancel = has_success_authorize and not has_success_capture
        can_refund = refundable_amount > Decimal("0")

        return OrderDetailResponse(
            order_id=order.id,
            order_status=order.status,
            amount=Decimal(str(order.amount)),
            currency=order.currency,
            created_at=order.created_at,
            transactions=transaction_summaries,
            last_successful_transaction=last_successful,
            refundable_amount=refundable_amount,
            can_capture=can_capture,
            can_cancel=can_cancel,
            can_refund=can_refund,
        )
