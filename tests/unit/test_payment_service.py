from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.payment_service import PaymentService
from app.repositories.payment_gateway.gateway_interface import GatewayResult
from app.schemas.payment import (
    PurchaseRequest,
    AuthorizeRequest,
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
    def __init__(self):
        self.charge_result = GatewayResult(True, "gw-purchase", "ok")
        self.authorize_result = GatewayResult(True, "gw-auth", "ok")
        self.capture_result = GatewayResult(True, "gw-capture", "ok")
        self.void_result = GatewayResult(True, "gw-void", "ok")
        self.refund_result = GatewayResult(True, "gw-refund", "ok")

    def charge_card(self, *args, **kwargs):
        return self.charge_result

    def authorize_card(self, *args, **kwargs):
        return self.authorize_result

    def capture_transaction(self, *args, **kwargs):
        return self.capture_result

    def void_transaction(self, *args, **kwargs):
        return self.void_result

    def refund_transaction(self, *args, **kwargs):
        return self.refund_result


def make_service():
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()
    service.gateway_repository = FakeGateway()
    return service


def test_purchase_success():
    service = make_service()
    user = SimpleNamespace(id=1)

    request = PurchaseRequest(
        amount=Decimal("10.00"),
        currency="USD",
        card_number="4111111111111111",
        expiry_month=12,
        expiry_year=2030,
        cvv="123",
    )

    result = service.process_purchase(user, request)

    assert result["status"] == "SUCCESS"
    order = service.order_repository.get_by_id(result["order_id"])
    assert order.status == "COMPLETED"
    txns = service.transaction_repository.get_by_order_id(order.id)
    assert txns[0].type == "PURCHASE"
    assert txns[0].status == "SUCCESS"


def test_authorize_success():
    service = make_service()
    user = SimpleNamespace(id=1)

    request = AuthorizeRequest(
        amount=Decimal("15.00"),
        currency="USD",
        card_number="4111111111111111",
        expiry_month=12,
        expiry_year=2030,
        cvv="123",
    )

    result = service.process_authorize(user, request)
    order = service.order_repository.get_by_id(result["order_id"])
    assert order.status == "PENDING"
    txns = service.transaction_repository.get_by_order_id(order.id)
    assert txns[0].type == "AUTHORIZE"
    assert txns[0].status == "SUCCESS"


def test_capture_success():
    service = make_service()
    user = SimpleNamespace(id=1)

    order = service.order_repository.create(1, 20.0, "USD", "PENDING")
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="AUTHORIZE",
        amount=20.0,
        status="SUCCESS",
        gateway_transaction_id="gw-auth",
    )

    result = service.process_capture(user, CaptureRequest(order_id=order.id, amount=Decimal("20.00")))
    order = service.order_repository.get_by_id(order.id)
    assert order.status == "COMPLETED"
    txns = service.transaction_repository.get_by_order_id(order.id)
    assert any(t.type == "CAPTURE" and t.status == "SUCCESS" for t in txns)
    assert result["status"] == "SUCCESS"


def test_cancel_success():
    service = make_service()
    user = SimpleNamespace(id=1)

    order = service.order_repository.create(1, 12.0, "USD", "PENDING")
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="AUTHORIZE",
        amount=12.0,
        status="SUCCESS",
        gateway_transaction_id="gw-auth",
    )

    result = service.process_cancel(user, CancelRequest(order_id=order.id))
    order = service.order_repository.get_by_id(order.id)
    assert order.status == "CANCELLED"
    txns = service.transaction_repository.get_by_order_id(order.id)
    assert any(t.type == "VOID" and t.status == "SUCCESS" for t in txns)
    assert result["status"] == "SUCCESS"


def test_refund_full_success():
    service = make_service()
    user = SimpleNamespace(id=1)

    order = service.order_repository.create(1, 30.0, "USD", "COMPLETED")
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="PURCHASE",
        amount=30.0,
        status="SUCCESS",
        gateway_transaction_id="gw-purchase",
    )

    request = RefundRequest(
        order_id=order.id,
        amount=Decimal("30.00"),
        last_four="1111",
        expiry_month=12,
        expiry_year=2030,
    )

    result = service.process_refund(user, request)
    order = service.order_repository.get_by_id(order.id)
    assert order.status == "REFUNDED"
    assert result["status"] == "SUCCESS"


def test_refund_partial_keeps_completed():
    service = make_service()
    user = SimpleNamespace(id=1)

    order = service.order_repository.create(1, 50.0, "USD", "COMPLETED")
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="CAPTURE",
        amount=50.0,
        status="SUCCESS",
        gateway_transaction_id="gw-capture",
    )

    request = RefundRequest(
        order_id=order.id,
        amount=Decimal("10.00"),
        last_four="1111",
        expiry_month=12,
        expiry_year=2030,
    )

    result = service.process_refund(user, request)
    order = service.order_repository.get_by_id(order.id)
    assert order.status == "COMPLETED"
    assert result["status"] == "SUCCESS"


def test_capture_without_authorize_fails():
    service = make_service()
    user = SimpleNamespace(id=1)

    order = service.order_repository.create(1, 20.0, "USD", "PENDING")

    with pytest.raises(PaymentNotFoundError):
        service.process_capture(user, CaptureRequest(order_id=order.id, amount=Decimal("20.00")))


def test_cancel_after_capture_fails():
    service = make_service()
    user = SimpleNamespace(id=1)

    order = service.order_repository.create(1, 20.0, "USD", "COMPLETED")
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

    with pytest.raises(InvalidTransactionStateError):
        service.process_cancel(user, CancelRequest(order_id=order.id))


def test_refund_exceeds_captured_amount():
    service = make_service()
    user = SimpleNamespace(id=1)

    order = service.order_repository.create(1, 20.0, "USD", "COMPLETED")
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="CAPTURE",
        amount=20.0,
        status="SUCCESS",
        gateway_transaction_id="gw-capture",
    )

    request = RefundRequest(
        order_id=order.id,
        amount=Decimal("25.00"),
        last_four="1111",
        expiry_month=12,
        expiry_year=2030,
    )

    with pytest.raises(InvalidTransactionStateError):
        service.process_refund(user, request)
