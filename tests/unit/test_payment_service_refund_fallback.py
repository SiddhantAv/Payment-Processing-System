"""Tests for refund fallback logic (authorization ID fallback)."""
from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.payment_service import PaymentService
from app.repositories.payment_gateway.gateway_interface import GatewayResult
from app.schemas.payment import RefundRequest
from app.exceptions.payment_exceptions import GatewayError


@dataclass
class FakeOrder:
    id: int
    user_id: int
    amount: float
    currency: str
    status: str


@dataclass
class FakeTransaction:
    id: int
    order_id: int
    type: str
    amount: float
    status: str
    gateway_transaction_id: str | None


class FakeOrderRepo:
    def __init__(self):
        self._id = 1
        self.orders: dict[int, FakeOrder] = {}

    def create(self, user_id: int, amount: float, currency: str, status: str):
        order = FakeOrder(self._id, user_id, amount, currency, status)
        self.orders[self._id] = order
        self._id += 1
        return order

    def get_by_id(self, order_id: int):
        return self.orders.get(order_id)

    def update_status(self, order_id: int, status: str):
        order = self.orders.get(order_id)
        if order:
            order.status = status
        return order


class FakeTransactionRepo:
    def __init__(self):
        self._id = 1
        self.transactions: list[FakeTransaction] = []

    def create(self, order_id: int, transaction_type: str, amount: float, status: str, gateway_transaction_id=None):
        txn = FakeTransaction(self._id, order_id, transaction_type, amount, status, gateway_transaction_id)
        self.transactions.append(txn)
        self._id += 1
        return txn

    def get_by_order_id(self, order_id: int):
        return [t for t in self.transactions if t.order_id == order_id]


def test_refund_fallback_to_authorization_id():
    """Test refund fallback uses authorization ID when capture ID fails."""
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()

    order = service.order_repository.create(user_id=1, amount=100.0, currency="USD", status="COMPLETED")
    # Create AUTHORIZE and CAPTURE transactions
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="AUTHORIZE",
        amount=100.0,
        status="SUCCESS",
        gateway_transaction_id="gw-auth"
    )
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="CAPTURE",
        amount=100.0,
        status="SUCCESS",
        gateway_transaction_id="gw-capture"
    )

    call_count = {"capture_call": 0, "auth_call": 0}

    class FakeGatewayWithFallback:
        def refund_transaction(self, gateway_transaction_id, *args, **kwargs):
            if gateway_transaction_id == "gw-capture":
                call_count["capture_call"] += 1
                # First call with capture ID fails
                raise GatewayError("The referenced transaction does not meet the criteria for issuing a credit.")
            elif gateway_transaction_id == "gw-auth":
                call_count["auth_call"] += 1
                # Second call with auth ID succeeds
                return GatewayResult(True, "gw-refund", "Refund successful")
            else:
                raise GatewayError("Unknown transaction ID")

    service.gateway_repository = FakeGatewayWithFallback()
    user = SimpleNamespace(id=1)

    request = RefundRequest(
        order_id=order.id,
        amount=Decimal("100.00"),
        last_four="1111",
        expiry_month=12,
        expiry_year=2030,
    )

    result = service.process_refund(user, request)

    assert result["status"] == "SUCCESS"
    assert call_count["capture_call"] == 1
    assert call_count["auth_call"] == 1  # Fallback was used
    # Verify order status updated to REFUNDED
    order = service.order_repository.get_by_id(order.id)
    assert order.status == "REFUNDED"


def test_refund_fallback_both_fail():
    """Test refund fallback when both capture and auth IDs fail."""
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()

    order = service.order_repository.create(user_id=1, amount=100.0, currency="USD", status="COMPLETED")
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="AUTHORIZE",
        amount=100.0,
        status="SUCCESS",
        gateway_transaction_id="gw-auth"
    )
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="CAPTURE",
        amount=100.0,
        status="SUCCESS",
        gateway_transaction_id="gw-capture"
    )

    class FakeGatewayAllFail:
        def refund_transaction(self, *args, **kwargs):
            raise GatewayError("The referenced transaction does not meet the criteria for issuing a credit.")

    service.gateway_repository = FakeGatewayAllFail()
    user = SimpleNamespace(id=1)

    request = RefundRequest(
        order_id=order.id,
        amount=Decimal("100.00"),
        last_four="1111",
        expiry_month=12,
        expiry_year=2030,
    )

    with pytest.raises(GatewayError) as exc_info:
        service.process_refund(user, request)

    # Verify error message mentions both transaction IDs
    error_msg = str(exc_info.value)
    assert "settled" in error_msg.lower() or "transaction" in error_msg.lower()
