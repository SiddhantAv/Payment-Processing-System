 # Project Structure

This document explains the folder layout and key modules of the Payment Processing System.

---

## Top-Level Layout

```
.
├── app/                 # Application code (API, services, repositories, models, schemas)
├── alembic/             # Database migrations
├── docker/              # Dockerfile, docker-compose, entrypoint
├── scripts/             # Utility scripts (db init, seed, connection test)
├── tests/               # Unit and integration tests
├── requirements.txt     # Dependencies (app + test)
├── alembic.ini          # Alembic configuration
└── README.md            # Project overview and setup instructions
```

---

## `app/` — Application Code

The main application package, organized by responsibility.

### `app/api/`
FastAPI routing and dependency injection.

- `routes/`  
  - `auth.py`: Login and registration endpoints  
  - `payments.py`: Purchase, authorize, capture, cancel, refund, and order views
- `dependencies.py`: JWT auth and DB session dependencies

### `app/core/`
Configuration and security utilities.

- `config.py`: Environment settings (DB URL, JWT, Authorize.Net)
- `security.py`: Password hashing + JWT token helpers

### `app/db/`
SQLAlchemy database setup.

- `base.py`: Declarative `Base`
- `session.py`: DB engine + session factory

### `app/models/`
SQLAlchemy ORM models (no separate domain layer).

- `user.py`: Users (auth)
- `order.py`: Orders
- `transaction.py`: Transactions

### `app/repositories/`
Data access layer for DB and external gateways.

- `database/`
  - `user_repository.py`: User queries
  - `order_repository.py`: Order queries
  - `transaction_repository.py`: Transaction queries
- `payment_gateway/`
  - `authorize_net_repository.py`: Authorize.Net SDK integration
  - `gateway_interface.py`: Minimal gateway interface + result wrapper

### `app/services/`
Business logic for authentication and payment flows.

- `auth_service.py`: Register + login
- `payment_service.py`: Purchase, authorize, capture, cancel, refund, order summaries

### `app/schemas/`
Pydantic request/response models.

- `auth.py`: Login/register schemas
- `payment.py`: Payment flow schemas + order/transaction summaries
- `common.py`: (reserved for shared schemas)

### `app/exceptions/`
Custom error types.

- `auth_exceptions.py`: Auth-specific errors
- `payment_exceptions.py`: Payment flow errors

### `app/main.py`
FastAPI application entry point. Registers routers and middleware.

---

## `alembic/` — Migrations

Database schema versioning.

- `env.py`: Alembic configuration (ties to app settings)
- `versions/`: Migration scripts

---

## `docker/` — Containerization

- `docker-compose.yml`: Local dev orchestration (API + Postgres)
- `Dockerfile`: App build
- `docker-entrypoint.sh`: Runs migrations then starts Uvicorn

---

## `scripts/` — Utility Scripts

- `init_db.py`: Create tables directly (non-migration use)
- `seed_data.py`: Seed demo users
- `test_db_connection.py`: Check DB connectivity

---

## `tests/` — Tests

Unit and integration tests with mocks for the payment gateway.

- `unit/`: Service-level tests (payment + auth)
- `integration/`: Minimal API tests for happy paths
- `conftest.py`: Shared fixtures and dependency overrides

---

## Key Design Notes

- **Single service**: No microservices or background workers.
- **ORM = domain**: SQLAlchemy models serve as the domain entities.
- **Gateway isolation**: Authorize.Net SDK logic is contained in one repository.
- **JWT protected**: All payment endpoints require JWT.
- **Minimal test strategy**: Focused on critical flows and regressions.
