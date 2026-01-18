
# Payment Processing System (FastAPI + PostgreSQL + Authorize.Net)

A FastAPI backend for payment processing with Authorize.Net Sandbox integration. It supports purchase, authorize, capture, cancel/void, refund, and developer utility endpoints for order/transaction inspection. JWT authentication protects all payment APIs.

## Key Features
- **JWT Authentication** (login + registration)
- **Authorize.Net Sandbox** integration (official SDK)
- **Payment Flows**: Purchase, Authorize, Capture, Cancel/Void, Refund (full/partial)
- **Orders + Transactions** persistence with PostgreSQL
- **Developer Utility APIs** for listing orders and transactions
- **Dockerized** local setup

---

## Project Structure (High Level)
- `app/` — FastAPI app (routes, services, repositories, models, schemas)
- `alembic/` — database migrations
- `scripts/` — utilities (db init, seed data, connection check)
- `docker/` — Dockerfile, docker-compose, entrypoint
- `tests/` — unit + integration tests

---

## Prerequisites
- Python 3.12+ (for local dev)
- PostgreSQL 15+ (if running locally)
- Docker + Docker Compose (recommended for local setup)

---

## Environment Variables
Create a `.env` file in the project root or export these variables:

```
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/pps_db

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Authorize.Net (Sandbox)
AUTHORIZE_NET_API_LOGIN_ID=your_sandbox_login_id
AUTHORIZE_NET_TRANSACTION_KEY=your_sandbox_transaction_key
AUTHORIZE_NET_ENVIRONMENT=sandbox

# Optional
DEBUG=False
```

---

## Database Setup
You can set up the database using **Docker** (recommended) or **local PostgreSQL**.

### Option A: Docker (Recommended)
From the project root:

```
docker compose -f docker/docker-compose.yml up --build
```

This will:
- Start PostgreSQL
- Run Alembic migrations automatically (via `docker-entrypoint.sh`)
- Start the FastAPI app on `http://localhost:8000`

### Option B: Local PostgreSQL
1) Create the database:
```
psql -U postgres -c "CREATE DATABASE pps_db;"
```

2) Install dependencies:
```
pip install -r requirements.txt
```

3) Run Alembic migrations:
```
alembic upgrade head
```

4) (Optional) Seed test users:
```
python scripts/seed_data.py
```

### Useful DB Scripts
- Test connection:
```
python scripts/test_db_connection.py
```
- Create tables directly (without Alembic, for quick setup only):
```
python scripts/init_db.py
```

---

## Running the Application

### Local (Uvicorn)
```
uvicorn app.main:app --reload
```

### Docker
```
docker compose -f docker/docker-compose.yml up --build
```

App will be available at:
- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

---

## Background Workers

**No background workers are required or configured.**  
All payment flows are synchronous and handled by the API itself.

If you add background workers later (e.g., for async settlement checks or retries), document them here and run them separately.

---

## Core API Endpoints (Overview)

### Auth
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`

### Payments
- `POST /api/v1/payments/purchase`
- `POST /api/v1/payments/authorize`
- `POST /api/v1/payments/capture`
- `POST /api/v1/payments/cancel`
- `POST /api/v1/payments/refund`

### Developer Utilities
- `GET /api/v1/payments/orders`
- `GET /api/v1/payments/orders/{order_id}`

---

## Testing
Run unit + integration tests:
```
pytest -q
```

To check coverage:
```
pytest --cov=app --cov-report=term-missing
```

---

## Notes & Tips
- **Authorize.Net Sandbox**: Refunds may require the transaction to be settled before they succeed.
- **Do not store card data**: Card details are used only for gateway calls.
- **JWT required**: All payment endpoints require `Authorization: Bearer <token>`.

---

## Troubleshooting
- Check `.env` values (especially `DATABASE_URL`, Authorize.Net credentials)
- Verify PostgreSQL is running
- Use `scripts/test_db_connection.py` for quick connectivity checks

---

## License
Internal / Evaluation Use Only
