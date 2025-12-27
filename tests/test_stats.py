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

def test_stats_empty(client):
    response = client.get("/stats")
    assert response.status_code == 200

    data = response.json()
    assert data["total_messages"] == 0
    assert data["senders_count"] == 0
    assert data["messages_per_sender"] == []
    assert data["first_message_ts"] is None
    assert data["last_message_ts"] is None

def test_stats_with_data(client):
    seed_message(client, "m1", "+919876543210", "2025-01-15T09:00:00Z", "First")
    seed_message(client, "m2", "+919876543210", "2025-01-15T10:00:00Z", "Second")
    seed_message(client, "m3", "+911234567890", "2025-01-15T11:00:00Z", "Third")
    seed_message(client, "m4", "+919876543210", "2025-01-15T12:00:00Z", "Fourth")

    response = client.get("/stats")
    assert response.status_code == 200

    data = response.json()
    assert data["total_messages"] == 4
    assert data["senders_count"] == 2
    assert len(data["messages_per_sender"]) == 2

    top_sender = data["messages_per_sender"][0]
    assert top_sender["from"] == "+919876543210"
    assert top_sender["count"] == 3

    assert data["first_message_ts"] == "2025-01-15T09:00:00Z"
    assert data["last_message_ts"] == "2025-01-15T12:00:00Z"

def test_stats_messages_per_sender_sorted(client):
    seed_message(client, "m1", "+919876543210", "2025-01-15T09:00:00Z", "A")
    seed_message(client, "m2", "+911234567890", "2025-01-15T10:00:00Z", "B")
    seed_message(client, "m3", "+911234567890", "2025-01-15T11:00:00Z", "C")
    seed_message(client, "m4", "+911234567890", "2025-01-15T12:00:00Z", "D")

    response = client.get("/stats")
    data = response.json()

    assert data["messages_per_sender"][0]["from"] == "+911234567890"
    assert data["messages_per_sender"][0]["count"] == 3
    assert data["messages_per_sender"][1]["from"] == "+919876543210"
    assert data["messages_per_sender"][1]["count"] == 1
