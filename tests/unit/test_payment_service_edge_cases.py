"""Additional edge case tests for payment service."""
from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.payment_service import PaymentService
from app.repositories.payment_gateway.gateway_interface import GatewayResult
from app.schemas.payment import (
    CaptureRequest,
    CancelRequest,
    RefundRequest,
)
from app.exceptions.payment_exceptions import (
    PaymentNotFoundError,
    InvalidTransactionStateError,
)


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

    def update_status(self, order_id: int, status: str):
        order = self.orders.get(order_id)
        if order:
            order.status = status
        return order

    def get_by_id(self, order_id: int):
        return self.orders.get(order_id)

    def get_by_id_and_user_id(self, order_id: int, user_id: int):
        order = self.orders.get(order_id)
        if order and order.user_id == user_id:
            return order
        return None


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


class FakeGateway:
    def capture_transaction(self, *args, **kwargs):
        return GatewayResult(True, "gw-capture", "ok")

    def void_transaction(self, *args, **kwargs):
        return GatewayResult(True, "gw-void", "ok")

    def refund_transaction(self, *args, **kwargs):
        return GatewayResult(True, "gw-refund", "ok")


def make_service():
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()
    service.gateway_repository = FakeGateway()
    return service


def test_capture_already_captured():
    """Test capture fails when order already captured."""
    service = make_service()
    user = SimpleNamespace(id=1)

    order = service.order_repository.create(user_id=1, amount=20.0, currency="USD", status="PENDING")
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="AUTHORIZE",
        amount=20.0,
        status="SUCCESS",
        gateway_transaction_id="gw-auth",
    )
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="CAPTURE",
        amount=20.0,
        status="SUCCESS",
        gateway_transaction_id="gw-capture",
    )

    with pytest.raises(InvalidTransactionStateError, match="already captured"):
        service.process_capture(user, CaptureRequest(order_id=order.id, amount=Decimal("20.00")))


def test_refund_with_previous_refunds():
    """Test partial refund after previous refunds."""
    service = make_service()
    user = SimpleNamespace(id=1)

    order = service.order_repository.create(user_id=1, amount=100.0, currency="USD", status="COMPLETED")
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="CAPTURE",
        amount=100.0,
        status="SUCCESS",
        gateway_transaction_id="gw-capture",
    )
    # Previous refund of 30
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="REFUND",
        amount=30.0,
        status="SUCCESS",
        gateway_transaction_id="gw-refund-1",
    )

    # Try to refund 50 more (should work, total refunded would be 80)
    request = RefundRequest(
        order_id=order.id,
        amount=Decimal("50.00"),
        last_four="1111",
        expiry_month=12,
        expiry_year=2030,
    )

    result = service.process_refund(user, request)
    assert result["status"] == "SUCCESS"

    # Verify order status still COMPLETED (not full refund)
    order = service.order_repository.get_by_id(order.id)
    assert order.status == "COMPLETED"


def test_refund_exceeds_remaining():
    """Test refund fails when amount exceeds remaining refundable."""
    service = make_service()
    user = SimpleNamespace(id=1)

    order = service.order_repository.create(user_id=1, amount=100.0, currency="USD", status="COMPLETED")
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="CAPTURE",
        amount=100.0,
        status="SUCCESS",
        gateway_transaction_id="gw-capture",
    )
    # Previous refund of 50
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="REFUND",
        amount=50.0,
        status="SUCCESS",
        gateway_transaction_id="gw-refund-1",
    )

    # Try to refund 60 more (would exceed remaining 50)
    request = RefundRequest(
        order_id=order.id,
        amount=Decimal("60.00"),
        last_four="1111",
        expiry_month=12,
        expiry_year=2030,
    )

    with pytest.raises(InvalidTransactionStateError, match="exceeds captured amount"):
        service.process_refund(user, request)
