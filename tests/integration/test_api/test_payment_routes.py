from app.services.payment_service import PaymentService


def test_purchase_success(client, auth_override, monkeypatch):
    def fake_process_purchase(self, user, purchase_request):
        return {
            "order_id": 1,
            "transaction_id": 1,
            "gateway_transaction_id": "gw-123",
            "status": "SUCCESS",
            "message": "ok",
        }

    monkeypatch.setattr(PaymentService, "process_purchase", fake_process_purchase)

    response = client.post(
        "/api/v1/payments/purchase",
        json={
            "amount": "10.00",
            "currency": "USD",
            "card_number": "4111111111111111",
            "expiry_month": 12,
            "expiry_year": 2030,
            "cvv": "123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == 1
    assert data["status"] == "SUCCESS"
