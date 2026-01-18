"""Tests for payment service list orders and get order detail methods."""
from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from datetime import datetime

import pytest

from app.services.payment_service import PaymentService
from app.exceptions.payment_exceptions import PaymentNotFoundError


@dataclass
class FakeOrder:
    id: int
    user_id: int
    amount: float
    currency: str
    status: str
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class FakeTransaction:
    id: int
    order_id: int
    type: str
    amount: float
    status: str
    gateway_transaction_id: str | None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


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

    def get_by_id_and_user_id(self, order_id: int, user_id: int):
        order = self.orders.get(order_id)
        if order and order.user_id == user_id:
            return order
        return None

    def get_by_user_id(self, user_id: int):
        return [o for o in self.orders.values() if o.user_id == user_id]

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


class FakeGateway:
    pass


def make_service():
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()
    service.gateway_repository = FakeGateway()
    return service


def test_list_orders_with_transactions():
    """Test list_orders_with_transactions returns orders with transactions."""
    service = make_service()
    user = SimpleNamespace(id=1)

    # Create two orders
    order1 = service.order_repository.create(user_id=1, amount=100.0, currency="USD", status="COMPLETED")
    order2 = service.order_repository.create(user_id=1, amount=50.0, currency="USD", status="PENDING")

    # Add transactions to order1
    service.transaction_repository.create(
        order_id=order1.id,
        transaction_type="PURCHASE",
        amount=100.0,
        status="SUCCESS",
        gateway_transaction_id="gw-1"
    )

    # Add transactions to order2
    service.transaction_repository.create(
        order_id=order2.id,
        transaction_type="AUTHORIZE",
        amount=50.0,
        status="SUCCESS",
        gateway_transaction_id="gw-2"
    )

    result = service.list_orders_with_transactions(user)

    assert len(result) == 2
    assert result[0].order_id == order1.id
    assert result[0].order_status == "COMPLETED"
    assert len(result[0].transactions) == 1
    assert result[1].order_id == order2.id
    assert len(result[1].transactions) == 1


def test_list_orders_empty():
    """Test list_orders_with_transactions returns empty list when no orders."""
    service = make_service()
    user = SimpleNamespace(id=1)

    result = service.list_orders_with_transactions(user)

    assert result == []
    assert len(result) == 0


def test_get_order_detail_success():
    """Test get_order_detail returns order details with flags."""
    service = make_service()
    user = SimpleNamespace(id=1)

    order = service.order_repository.create(user_id=1, amount=100.0, currency="USD", status="COMPLETED")
    # Use CAPTURE instead of PURCHASE for refundable calculation
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="CAPTURE",
        amount=100.0,
        status="SUCCESS",
        gateway_transaction_id="gw-1"
    )

    result = service.get_order_detail(user, order.id)

    assert result.order_id == order.id
    assert result.order_status == "COMPLETED"
    assert len(result.transactions) == 1
    assert result.can_refund is True
    assert result.refundable_amount == Decimal("100.00")
    assert result.last_successful_transaction is not None


def test_get_order_detail_with_authorize():
    """Test get_order_detail with authorize transaction."""
    service = make_service()
    user = SimpleNamespace(id=1)

    order = service.order_repository.create(user_id=1, amount=100.0, currency="USD", status="PENDING")
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="AUTHORIZE",
        amount=100.0,
        status="SUCCESS",
        gateway_transaction_id="gw-auth"
    )

    result = service.get_order_detail(user, order.id)

    assert result.can_capture is True
    assert result.can_cancel is True
    assert result.can_refund is False  # No capture yet


def test_get_order_detail_order_not_found():
    """Test get_order_detail raises error when order not found."""
    service = make_service()
    user = SimpleNamespace(id=1)

    with pytest.raises(PaymentNotFoundError, match="Order not found"):
        service.get_order_detail(user, 999)


def test_get_order_detail_wrong_user():
    """Test get_order_detail raises error when order belongs to different user."""
    service = make_service()
    user1 = SimpleNamespace(id=1)
    user2 = SimpleNamespace(id=2)

    order = service.order_repository.create(user_id=1, amount=100.0, currency="USD", status="COMPLETED")

    with pytest.raises(PaymentNotFoundError, match="Order not found"):
        service.get_order_detail(user2, order.id)  # user2 tries to access user1's order


def test_get_order_detail_with_refunds():
    """Test get_order_detail calculates refundable amount correctly."""
    service = make_service()
    user = SimpleNamespace(id=1)

    order = service.order_repository.create(user_id=1, amount=100.0, currency="USD", status="COMPLETED")
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="CAPTURE",
        amount=100.0,
        status="SUCCESS",
        gateway_transaction_id="gw-capture"
    )
    # Previous refund of 30
    service.transaction_repository.create(
        order_id=order.id,
        transaction_type="REFUND",
        amount=30.0,
        status="SUCCESS",
        gateway_transaction_id="gw-refund"
    )

    result = service.get_order_detail(user, order.id)

    assert result.refundable_amount == Decimal("70.00")  # 100 - 30
    assert result.can_refund is True
