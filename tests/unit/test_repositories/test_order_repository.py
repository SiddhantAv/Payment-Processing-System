"""Tests for OrderRepository."""
import pytest
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, Mock

from app.repositories.database.order_repository import OrderRepository
from app.models.order import Order


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def order_repo(mock_db):
    """Create OrderRepository instance with mocked DB."""
    return OrderRepository(mock_db)


def test_get_by_id_found(order_repo, mock_db):
    """Test get_by_id returns order when found."""
    mock_order = MagicMock(spec=Order)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_order

    result = order_repo.get_by_id(1)

    assert result == mock_order
    mock_db.query.assert_called_once_with(Order)


def test_get_by_id_not_found(order_repo, mock_db):
    """Test get_by_id returns None when not found."""
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = order_repo.get_by_id(999)

    assert result is None


def test_create(order_repo, mock_db):
    """Test create adds order to database."""
    from unittest.mock import patch
    mock_order = MagicMock(spec=Order)
    mock_db.add = Mock()
    mock_db.commit = Mock()
    mock_db.refresh = Mock()

    # Mock the Order model constructor
    with patch('app.repositories.database.order_repository.Order', return_value=mock_order):
        result = order_repo.create(user_id=1, amount=100.0, currency="USD", status="PENDING")

    assert result == mock_order
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_order)


def test_update_status(order_repo, mock_db):
    """Test update_status updates order status."""
    mock_order = MagicMock(spec=Order)
    mock_order.id = 1
    mock_db.query.return_value.filter.return_value.first.return_value = mock_order

    result = order_repo.update_status(1, "COMPLETED")

    assert mock_order.status == "COMPLETED"
    mock_db.commit.assert_called_once()
    assert result == mock_order


def test_update_status_not_found(order_repo, mock_db):
    """Test update_status returns None when order not found."""
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = order_repo.update_status(999, "COMPLETED")

    assert result is None
    # commit should not be called when order is not found
    mock_db.commit.assert_not_called()


def test_get_by_user_id(order_repo, mock_db):
    """Test get_by_user_id returns list of orders."""
    mock_orders = [MagicMock(spec=Order), MagicMock(spec=Order)]
    # Note: get_by_user_id uses .all() not .order_by().all()
    mock_db.query.return_value.filter.return_value.all.return_value = mock_orders

    result = order_repo.get_by_user_id(1)

    assert result == mock_orders
    assert len(result) == 2


def test_get_by_id_and_user_id_found(order_repo, mock_db):
    """Test get_by_id_and_user_id returns order when found."""
    mock_order = MagicMock(spec=Order)
    mock_order.user_id = 1
    mock_db.query.return_value.filter.return_value.first.return_value = mock_order

    result = order_repo.get_by_id_and_user_id(order_id=1, user_id=1)

    assert result == mock_order


def test_get_by_id_and_user_id_not_found(order_repo, mock_db):
    """Test get_by_id_and_user_id returns None when not found."""
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = order_repo.get_by_id_and_user_id(order_id=999, user_id=1)

    assert result is None
