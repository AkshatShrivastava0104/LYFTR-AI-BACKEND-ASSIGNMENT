import json
from tests.conftest import compute_signature

def test_webhook_invalid_signature(client):
    body = json.dumps({
        "message_id": "m1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    })

    response = client.post(
        "/webhook",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": "invalid_signature"
        }
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid signature"

def test_webhook_valid_insert(client):
    body = json.dumps({
        "message_id": "m1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    })

    signature = compute_signature(body)

    response = client.post(
        "/webhook",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature
        }
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_webhook_duplicate(client):
    body = json.dumps({
        "message_id": "m2",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    })

    signature = compute_signature(body)
    headers = {
        "Content-Type": "application/json",
        "X-Signature": signature
    }

    response1 = client.post("/webhook", data=body, headers=headers)
    assert response1.status_code == 200

    response2 = client.post("/webhook", data=body, headers=headers)
    assert response2.status_code == 200
    assert response2.json() == {"status": "ok"}

def test_webhook_validation_error(client):
    body = json.dumps({
        "message_id": "",
        "from": "invalid",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    })

    signature = compute_signature(body)

    response = client.post(
        "/webhook",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature
        }
    )

    assert response.status_code == 422

def test_webhook_missing_signature(client):
    body = json.dumps({
        "message_id": "m3",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    })

    response = client.post(
        "/webhook",
        data=body,
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 401
