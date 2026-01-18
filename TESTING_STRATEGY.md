# Testing Strategy

This document outlines the test plan and strategy for the Payment Processing System.

---

## 1. Goals

- Validate business-critical payment flows
- Prevent regressions across core APIs
- Maintain ≥60% code coverage with practical tests
- Keep tests fast, deterministic, and easy to maintain

---

## 2. Test Scope & Priorities

### Priority 1: Service Layer (Unit Tests)
Validate the core payment and authentication logic without hitting real gateways.

**Coverage targets:**
- Purchase (authorize + capture)
- Authorize-only
- Capture
- Cancel/Void
- Refund (full + partial)
- Auth registration + login

### Priority 2: API Layer (Minimal Integration Tests)
Validate routing, request validation, and basic responses.

**Coverage targets:**
- `/auth/register` happy path
- `/auth/login` happy path
- `/payments/purchase` happy path

### Priority 3: Developer Utility APIs
Ensure read-only endpoints return valid structures.

**Coverage targets:**
- `/payments/orders`
- `/payments/orders/{order_id}`

---

## 3. Testing Types

### Unit Tests
Focus on isolated components:
- Service layer methods
- Repository logic (only if complex)
- Utility functions (JWT, validation, etc.)

### Integration Tests
Minimal end-to-end tests with dependency overrides and mocks:
- FastAPI routing + schemas
- JWT guards (via dependency override)

### Non-Goals
We explicitly avoid:
- End-to-end tests with real Authorize.Net sandbox
- Load/performance testing (out of scope here)
- Security penetration testing

---

## 4. Mocking Strategy

### Payment Gateway
All Authorize.Net SDK calls are mocked.

Reason:
- Prevent flaky network calls
- Keep tests deterministic
- Avoid sandbox rate limits

### Database
Use mocked session or in-memory DB for unit tests.
For integration tests, dependency overrides inject mocked DB/session.

---

## 5. Coverage Targets

- **Minimum:** 60% overall coverage
- Focus on high-risk areas (payment flows, state transitions)

Command:
```
pytest --cov=app --cov-report=term-missing
```

---

## 6. Test Case Planning

### Payment Service
| Flow | Scenario | Expected Outcome |
|------|---------|------------------|
| Purchase | Success | Order → COMPLETED, Transaction SUCCESS |
| Purchase | Gateway error | Order → FAILED, Transaction FAILED |
| Authorize | Success | Order → PENDING, Transaction SUCCESS |
| Capture | Missing auth | Error (400) |
| Capture | Success | Order → COMPLETED, Transaction SUCCESS |
| Cancel | Already captured | Error (409) |
| Cancel | Success | Order → CANCELLED, Transaction SUCCESS |
| Refund | Partial | Order stays COMPLETED |
| Refund | Full | Order → REFUNDED |
| Refund | Exceeds captured | Error (400) |

### Auth Service
| Scenario | Expected Outcome |
|----------|------------------|
| Register new user | User created |
| Register duplicate | Conflict error |
| Login valid | JWT token returned |
| Login invalid | Error |

### API (Integration)
| Endpoint | Scenario | Expected Outcome |
|----------|---------|------------------|
| /auth/register | Success | 201 Created |
| /auth/login | Success | 200 OK + token |
| /payments/purchase | Success | 200 OK + transaction |

---

## 7. Test Data Strategy

- Use small, deterministic data
- Avoid real card numbers (use test values)
- Seed users only when required for auth tests

---

## 8. Tooling

- **pytest** for unit/integration tests
- **pytest-cov** for coverage
- **pytest-mock** or `unittest.mock` for mocking

---

## 9. Execution Plan

1. Run unit tests first (fast feedback)
2. Run integration tests
3. Check coverage and adjust if below target

---

## 10. Maintenance Notes

- Keep tests aligned with service logic changes
- Avoid over-mocking internal logic
- Update tests when new flows are added

