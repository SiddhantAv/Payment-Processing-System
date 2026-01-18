"""Additional tests for payment service error cases."""
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
    InvalidCardError,
    PaymentDeclinedError,
    GatewayError,
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


class FakeGatewayWithErrors:
    """Gateway that raises errors for testing."""

    def charge_card(self, *args, **kwargs):
        raise InvalidCardError("Invalid card details")

    def authorize_card(self, *args, **kwargs):
        raise PaymentDeclinedError("Payment declined")

    def capture_transaction(self, *args, **kwargs):
        raise GatewayError("Gateway error")

    def void_transaction(self, *args, **kwargs):
        raise GatewayError("Gateway error")

    def refund_transaction(self, *args, **kwargs):
        raise GatewayError("Gateway error")


def make_service_with_errors():
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()
    service.gateway_repository = FakeGatewayWithErrors()
    return service


def test_purchase_invalid_card_error():
    """Test purchase fails with invalid card error."""
    service = make_service_with_errors()
    user = SimpleNamespace(id=1)

    request = PurchaseRequest(
        amount=Decimal("10.00"),
        currency="USD",
        card_number="4111111111111111",
        expiry_month=12,
        expiry_year=2030,
        cvv="123",
    )

    with pytest.raises(InvalidCardError):
        service.process_purchase(user, request)

    # Verify failed transaction was created
    orders = list(service.order_repository.orders.values())
    assert len(orders) == 1
    assert orders[0].status == "FAILED"
    txns = service.transaction_repository.get_by_order_id(orders[0].id)
    assert txns[0].status == "FAILED"


def test_purchase_payment_declined_error():
    """Test purchase fails with payment declined error."""
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()

    class FakeGatewayDeclined:
        def charge_card(self, *args, **kwargs):
            raise PaymentDeclinedError("Payment declined")

    service.gateway_repository = FakeGatewayDeclined()
    user = SimpleNamespace(id=1)

    request = PurchaseRequest(
        amount=Decimal("10.00"),
        currency="USD",
        card_number="4111111111111111",
        expiry_month=12,
        expiry_year=2030,
        cvv="123",
    )

    with pytest.raises(PaymentDeclinedError):
        service.process_purchase(user, request)


def test_authorize_invalid_card_error():
    """Test authorize fails with invalid card error."""
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()

    class FakeGatewayInvalid:
        def authorize_card(self, *args, **kwargs):
            raise InvalidCardError("Invalid card")

    service.gateway_repository = FakeGatewayInvalid()
    user = SimpleNamespace(id=1)

    request = AuthorizeRequest(
        amount=Decimal("15.00"),
        currency="USD",
        card_number="4111111111111111",
        expiry_month=12,
        expiry_year=2030,
        cvv="123",
    )

    with pytest.raises(InvalidCardError):
        service.process_authorize(user, request)


def test_capture_order_not_found():
    """Test capture fails when order not found."""
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()

    class FakeGateway:
        def capture_transaction(self, *args, **kwargs):
            return GatewayResult(True, "gw-capture", "ok")

    service.gateway_repository = FakeGateway()
    user = SimpleNamespace(id=1)

    with pytest.raises(PaymentNotFoundError, match="Order not found"):
        service.process_capture(user, CaptureRequest(order_id=999, amount=Decimal("10.00")))


def test_capture_order_wrong_user():
    """Test capture fails when order belongs to different user."""
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()

    order = service.order_repository.create(user_id=2, amount=10.0, currency="USD", status="PENDING")

    class FakeGateway:
        def capture_transaction(self, *args, **kwargs):
            return GatewayResult(True, "gw-capture", "ok")

    service.gateway_repository = FakeGateway()
    user = SimpleNamespace(id=1)  # Different user

    with pytest.raises(PaymentNotFoundError, match="Order not found"):
        service.process_capture(user, CaptureRequest(order_id=order.id, amount=Decimal("10.00")))


def test_cancel_order_not_found():
    """Test cancel fails when order not found."""
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()

    class FakeGateway:
        def void_transaction(self, *args, **kwargs):
            return GatewayResult(True, "gw-void", "ok")

    service.gateway_repository = FakeGateway()
    user = SimpleNamespace(id=1)

    with pytest.raises(PaymentNotFoundError, match="Order not found"):
        service.process_cancel(user, CancelRequest(order_id=999))


def test_refund_order_not_found():
    """Test refund fails when order not found."""
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()

    class FakeGateway:
        def refund_transaction(self, *args, **kwargs):
            return GatewayResult(True, "gw-refund", "ok")

    service.gateway_repository = FakeGateway()
    user = SimpleNamespace(id=1)

    request = RefundRequest(
        order_id=999,
        amount=Decimal("10.00"),
        last_four="1111",
        expiry_month=12,
        expiry_year=2030,
    )

    with pytest.raises(PaymentNotFoundError, match="Order not found"):
        service.process_refund(user, request)


def test_refund_no_capture_found():
    """Test refund fails when no capture transaction exists."""
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()

    order = service.order_repository.create(user_id=1, amount=10.0, currency="USD", status="PENDING")
    # Create AUTHORIZE but no CAPTURE/PURCHASE
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="AUTHORIZE",
        amount=10.0,
        status="SUCCESS",
        gateway_transaction_id="gw-auth",
    )

    class FakeGateway:
        def refund_transaction(self, *args, **kwargs):
            return GatewayResult(True, "gw-refund", "ok")

    service.gateway_repository = FakeGateway()
    user = SimpleNamespace(id=1)

    request = RefundRequest(
        order_id=order.id,
        amount=Decimal("10.00"),
        last_four="1111",
        expiry_month=12,
        expiry_year=2030,
    )

    with pytest.raises(PaymentNotFoundError, match="No successful capture"):
        service.process_refund(user, request)


def test_capture_gateway_error():
    """Test capture handles gateway errors."""
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()

    order = service.order_repository.create(user_id=1, amount=10.0, currency="USD", status="PENDING")
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="AUTHORIZE",
        amount=10.0,
        status="SUCCESS",
        gateway_transaction_id="gw-auth",
    )

    class FakeGatewayError:
        def capture_transaction(self, *args, **kwargs):
            raise GatewayError("Gateway error")

    service.gateway_repository = FakeGatewayError()
    user = SimpleNamespace(id=1)

    with pytest.raises(GatewayError):
        service.process_capture(user, CaptureRequest(order_id=order.id, amount=Decimal("10.00")))

    # Verify failed transaction was created
    txns = service.transaction_repository.get_by_order_id(order.id)
    capture_txns = [t for t in txns if t.type == "CAPTURE"]
    assert len(capture_txns) == 1
    assert capture_txns[0].status == "FAILED"


def test_cancel_gateway_error():
    """Test cancel handles gateway errors."""
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()

    order = service.order_repository.create(user_id=1, amount=10.0, currency="USD", status="PENDING")
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="AUTHORIZE",
        amount=10.0,
        status="SUCCESS",
        gateway_transaction_id="gw-auth",
    )

    class FakeGatewayError:
        def void_transaction(self, *args, **kwargs):
            raise GatewayError("Gateway error")

    service.gateway_repository = FakeGatewayError()
    user = SimpleNamespace(id=1)

    with pytest.raises(GatewayError):
        service.process_cancel(user, CancelRequest(order_id=order.id))

    # Verify failed transaction was created
    txns = service.transaction_repository.get_by_order_id(order.id)
    void_txns = [t for t in txns if t.type == "VOID"]
    assert len(void_txns) == 1
    assert void_txns[0].status == "FAILED"


def test_refund_gateway_error():
    """Test refund handles gateway errors."""
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()

    order = service.order_repository.create(user_id=1, amount=10.0, currency="USD", status="COMPLETED")
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="CAPTURE",
        amount=10.0,
        status="SUCCESS",
        gateway_transaction_id="gw-capture",
    )

    class FakeGatewayError:
        def refund_transaction(self, *args, **kwargs):
            raise GatewayError("Gateway error")

    service.gateway_repository = FakeGatewayError()
    user = SimpleNamespace(id=1)

    request = RefundRequest(
        order_id=order.id,
        amount=Decimal("10.00"),
        last_four="1111",
        expiry_month=12,
        expiry_year=2030,
    )

    with pytest.raises(GatewayError):
        service.process_refund(user, request)

    # Verify failed transaction was created
    txns = service.transaction_repository.get_by_order_id(order.id)
    refund_txns = [t for t in txns if t.type == "REFUND"]
    assert len(refund_txns) == 1
    assert refund_txns[0].status == "FAILED"
