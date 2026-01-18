# Test Report

## Summary
Test suite executed successfully with strong coverage across core payment and auth logic.

---

## Test Execution

**Command:**
```
pytest --cov=app --cov-report=term-missing
```

**Status:** Executed successfully  
**Date:** 2026-01-18  
**Result:** 74 passed, 17 warnings

---

## Coverage Summary

| Metric | Value |
|--------|-------|
| Total Coverage | **87%** |
| Unit Tests | Covered (majority of suite) |
| Integration Tests | Minimal happy-path coverage |

---

## Coverage Focus Areas

- Payment flows: purchase, authorize, capture, cancel/void, refund
- Authentication: register, login, invalid credentials
- Minimal API integration: `/auth/register`, `/auth/login`, `/payments/purchase`

---

## How to Generate Coverage Locally

1) Install dependencies:
```
pip install -r requirements.txt
```

2) Run tests with coverage:
```
pytest --cov=app --cov-report=term-missing
```

3) (Optional) Generate HTML report:
```
pytest --cov=app --cov-report=html
```

---

## Key Coverage Notes

Lowest coverage areas (by file):
- `app/api/routes/payments.py` — 30% (most error branches not hit in integration tests)
- `app/db/session.py` — 60% (DB session lifecycle not exercised in tests)
- `app/api/routes/auth.py` — 75% (registration error paths not covered)

Overall coverage exceeds the 60% target with strong service-level coverage.

## Notes
- Test warnings are related to deprecated Pydantic/SQLAlchemy patterns; they do not affect test correctness.
- Keep this report updated after any major feature changes.
