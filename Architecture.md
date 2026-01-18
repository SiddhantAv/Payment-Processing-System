# Architecture Overview

This document provides:
- A concise overview of implemented payment flows
- API endpoints (simple documentation)
- Database schema and entity relationships

---

## Implemented Flows

### 1) Purchase (Authorize + Capture)
- One-step payment: authorizes and captures immediately
- Creates `Order` and `Transaction` (type `PURCHASE`)
- Order status → `COMPLETED` on success, `FAILED` on error

### 2) Authorize (Hold Funds)
- Authorizes funds without capture
- Creates `Order` and `Transaction` (type `AUTHORIZE`)
- Order status remains `PENDING` on success, `FAILED` on error

### 3) Capture
- Captures funds from a prior successful authorization
- Creates `Transaction` (type `CAPTURE`)
- Order status → `COMPLETED` on success

### 4) Cancel / Void
- Voids a prior authorization (must be before capture)
- Creates `Transaction` (type `VOID`)
- Order status → `CANCELLED` on success

### 5) Refund (Full / Partial)
- Refunds against a prior capture or purchase
- Creates `Transaction` (type `REFUND`)
- Order status → `REFUNDED` on full refund, stays `COMPLETED` on partial

### 6) Developer Utilities
- List orders with transactions
- Retrieve order details including flags: `can_capture`, `can_cancel`, `can_refund`, `refundable_amount`

---

## API Endpoints

Base URL: `/api/v1`

### Auth
- `POST /auth/register`
  - Request: `email`, `password`
  - Response: `id`, `email`, `created_at`
- `POST /auth/login`
  - Request: `email`, `password`
  - Response: `access_token`, `token_type`

### Payments (JWT Required)
- `POST /payments/purchase`
  - Request: `amount`, `currency`, `card_number`, `expiry_month`, `expiry_year`, `cvv`
  - Response: `order_id`, `transaction_id`, `gateway_transaction_id`, `status`, `message`

- `POST /payments/authorize`
  - Request: `amount`, `currency`, `card_number`, `expiry_month`, `expiry_year`, `cvv`
  - Response: `order_id`, `transaction_id`, `gateway_transaction_id`, `status`, `message`

- `POST /payments/capture`
  - Request: `order_id`, `amount`
  - Response: `order_id`, `transaction_id`, `gateway_transaction_id`, `status`, `message`

- `POST /payments/cancel`
  - Request: `order_id`
  - Response: `order_id`, `transaction_id`, `gateway_transaction_id`, `status`, `message`

- `POST /payments/refund`
  - Request: `order_id`, `amount`, `last_four`, `expiry_month`, `expiry_year`
  - Response: `order_id`, `transaction_id`, `gateway_transaction_id`, `status`, `message`

### Developer Utilities (JWT Required)
- `GET /payments/orders`
  - Response: list of order summaries with transactions

- `GET /payments/orders/{order_id}`
  - Response: order details + transaction history + flags

---

## Database Schema

### Entity: `users`
- `id` (PK)
- `email` (unique)
- `hashed_password`
- `created_at`

### Entity: `orders`
- `id` (PK)
- `user_id` (FK → users.id)
- `amount`
- `currency`
- `status`
- `created_at`
- `updated_at`

### Entity: `transactions`
- `id` (PK)
- `order_id` (FK → orders.id)
- `gateway_transaction_id` (nullable)
- `type` (PURCHASE / AUTHORIZE / CAPTURE / VOID / REFUND)
- `status` (INITIATED / SUCCESS / FAILED)
- `amount`
- `created_at`

---

## Relationships

```
users (1) ──── (N) orders
orders (1) ──── (N) transactions
```

- A user can have many orders.
- An order can have many transactions (each payment operation creates a transaction).

---

## Notes

- Card data is never stored in the database.
- All payment endpoints require JWT authentication.
- Gateway integration is isolated in `AuthorizeNetRepository`.
