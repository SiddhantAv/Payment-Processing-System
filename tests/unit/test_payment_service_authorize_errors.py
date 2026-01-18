"""Tests for authorize error handling."""
from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.payment_service import PaymentService
from app.repositories.payment_gateway.gateway_interface import GatewayResult
from app.schemas.payment import AuthorizeRequest
from app.exceptions.payment_exceptions import (
    GatewayError,
    PaymentDeclinedError,
    InvalidCardError,
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


def test_authorize_gateway_error():
    """Test authorize handles gateway errors."""
    service = PaymentService(db=None)
    service.order_repository = FakeOrderRepo()
    service.transaction_repository = FakeTransactionRepo()

    class FakeGatewayError:
        def authorize_card(self, *args, **kwargs):
            raise GatewayError("Gateway error")

    service.gateway_repository = FakeGatewayError()
    user = SimpleNamespace(id=1)

    request = AuthorizeRequest(
        amount=Decimal("15.00"),
        currency="USD",
        card_number="4111111111111111",
        expiry_month=12,
        expiry_year=2030,
        cvv="123",
    )

    with pytest.raises(GatewayError):
        service.process_authorize(user, request)

    # Verify failed transaction was created
    orders = list(service.order_repository.orders.values())
    assert len(orders) == 1
    assert orders[0].status == "FAILED"
    txns = service.transaction_repository.get_by_order_id(orders[0].id)
    assert txns[0].status == "FAILED"
