"""Tests for TransactionRepository."""
import pytest
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, Mock

from app.repositories.database.transaction_repository import TransactionRepository
from app.models.transaction import Transaction


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def transaction_repo(mock_db):
    """Create TransactionRepository instance with mocked DB."""
    return TransactionRepository(mock_db)


def test_get_by_id_found(transaction_repo, mock_db):
    """Test get_by_id returns transaction when found."""
    mock_transaction = MagicMock(spec=Transaction)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_transaction

    result = transaction_repo.get_by_id(1)

    assert result == mock_transaction
    mock_db.query.assert_called_once_with(Transaction)


def test_get_by_id_not_found(transaction_repo, mock_db):
    """Test get_by_id returns None when not found."""
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = transaction_repo.get_by_id(999)

    assert result is None


def test_create(transaction_repo, mock_db):
    """Test create adds transaction to database."""
    from unittest.mock import patch
    mock_transaction = MagicMock(spec=Transaction)
    mock_db.add = Mock()
    mock_db.commit = Mock()
    mock_db.refresh = Mock()

    # Mock the Transaction model constructor
    with patch('app.repositories.database.transaction_repository.Transaction', return_value=mock_transaction):
        result = transaction_repo.create(
            order_id=1,
            transaction_type="PURCHASE",
            amount=100.0,
            status="SUCCESS",
            gateway_transaction_id="gw-123"
        )

    assert result == mock_transaction
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_transaction)


def test_get_by_order_id(transaction_repo, mock_db):
    """Test get_by_order_id returns list of transactions."""
    mock_transactions = [MagicMock(spec=Transaction), MagicMock(spec=Transaction)]
    # Note: get_by_order_id uses .all() not .order_by().all()
    mock_db.query.return_value.filter.return_value.all.return_value = mock_transactions

    result = transaction_repo.get_by_order_id(1)

    assert result == mock_transactions
    assert len(result) == 2


def test_get_by_gateway_transaction_id(transaction_repo, mock_db):
    """Test get_by_gateway_transaction_id returns transaction when found."""
    mock_transaction = MagicMock(spec=Transaction)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_transaction

    result = transaction_repo.get_by_gateway_transaction_id("gw-123")

    assert result == mock_transaction


def test_get_by_gateway_transaction_id_not_found(transaction_repo, mock_db):
    """Test get_by_gateway_transaction_id returns None when not found."""
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = transaction_repo.get_by_gateway_transaction_id("nonexistent")

    assert result is None


def test_update_status(transaction_repo, mock_db):
    """Test update_status updates transaction status."""
    mock_transaction = MagicMock(spec=Transaction)
    mock_transaction.id = 1
    mock_db.query.return_value.filter.return_value.first.return_value = mock_transaction

    result = transaction_repo.update_status(1, "FAILED")

    assert mock_transaction.status == "FAILED"
    mock_db.commit.assert_called_once()
    assert result == mock_transaction


def test_update_status_not_found(transaction_repo, mock_db):
    """Test update_status returns None when transaction not found."""
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = transaction_repo.update_status(999, "FAILED")

    assert result is None
    # commit should not be called when transaction is not found
    mock_db.commit.assert_not_called()
