import json
from tests.conftest import compute_signature

def seed_message(client, message_id: str, from_num: str, ts: str, text: str):
    body = json.dumps({
        "message_id": message_id,
        "from": from_num,
        "to": "+14155550100",
        "ts": ts,
        "text": text
    })

    signature = compute_signature(body)

    client.post(
        "/webhook",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature
        }
    )

def test_messages_list_empty(client):
    response = client.get("/messages")
    assert response.status_code == 200

    data = response.json()
    assert data["data"] == []
    assert data["total"] == 0
    assert data["limit"] == 50
    assert data["offset"] == 0

def test_messages_list_with_data(client):
    seed_message(client, "m1", "+919876543210", "2025-01-15T09:00:00Z", "First")
    seed_message(client, "m2", "+919876543210", "2025-01-15T10:00:00Z", "Second")
    seed_message(client, "m3", "+911234567890", "2025-01-15T11:00:00Z", "Third")

    response = client.get("/messages")
    assert response.status_code == 200

    data = response.json()
    assert len(data["data"]) == 3
    assert data["total"] == 3
    assert data["data"][0]["message_id"] == "m1"
    assert data["data"][1]["message_id"] == "m2"
    assert data["data"][2]["message_id"] == "m3"

def test_messages_pagination(client):
    seed_message(client, "m1", "+919876543210", "2025-01-15T09:00:00Z", "First")
    seed_message(client, "m2", "+919876543210", "2025-01-15T10:00:00Z", "Second")
    seed_message(client, "m3", "+911234567890", "2025-01-15T11:00:00Z", "Third")

    response = client.get("/messages?limit=2&offset=0")
    data = response.json()
    assert len(data["data"]) == 2
    assert data["total"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 0

    response = client.get("/messages?limit=2&offset=2")
    data = response.json()
    assert len(data["data"]) == 1
    assert data["total"] == 3

def test_messages_filter_by_from(client):
    seed_message(client, "m1", "+919876543210", "2025-01-15T09:00:00Z", "First")
    seed_message(client, "m2", "+919876543210", "2025-01-15T10:00:00Z", "Second")
    seed_message(client, "m3", "+911234567890", "2025-01-15T11:00:00Z", "Third")

    response = client.get("/messages?from=%2B919876543210")
    data = response.json()
    assert data["total"] == 2
    assert all(msg["from"] == "+919876543210" for msg in data["data"])

def test_messages_filter_by_since(client):
    seed_message(client, "m1", "+919876543210", "2025-01-15T09:00:00Z", "First")
    seed_message(client, "m2", "+919876543210", "2025-01-15T10:00:00Z", "Second")
    seed_message(client, "m3", "+911234567890", "2025-01-15T11:00:00Z", "Third")

    response = client.get("/messages?since=2025-01-15T10:30:00Z")
    data = response.json()
    assert data["total"] == 1
    assert data["data"][0]["message_id"] == "m3"

def test_messages_filter_by_q(client):
    seed_message(client, "m1", "+919876543210", "2025-01-15T09:00:00Z", "Hello World")
    seed_message(client, "m2", "+919876543210", "2025-01-15T10:00:00Z", "Goodbye")
    seed_message(client, "m3", "+911234567890", "2025-01-15T11:00:00Z", "Hello Again")

    response = client.get("/messages?q=Hello")
    data = response.json()
    assert data["total"] == 2
    assert all("Hello" in msg["text"] for msg in data["data"])

def test_messages_ordering(client):
    seed_message(client, "m2", "+919876543210", "2025-01-15T10:00:00Z", "Second")
    seed_message(client, "m1", "+919876543210", "2025-01-15T09:00:00Z", "First")
    seed_message(client, "m3", "+911234567890", "2025-01-15T09:00:00Z", "Third")

    response = client.get("/messages")
    data = response.json()

    assert data["data"][0]["message_id"] == "m1"
    assert data["data"][1]["message_id"] == "m3"
    assert data["data"][2]["message_id"] == "m2"
