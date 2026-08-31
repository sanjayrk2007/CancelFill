from datetime import datetime, timezone, timedelta

def test_waitlist_registration_and_priority(client):
    now = datetime.now(timezone.utc)
    
    # 1. Create a slot
    slot_res = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "test_service_slot",
            "start_time": (now + timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat()
        }
    )
    slot_id = slot_res.json()["id"]

    # 2. Register Customer B (joined 5 minutes ago)
    joined_b = (now - timedelta(minutes=5)).isoformat()
    client.post(
        "/api/v1/waitlist",
        json={
            "slot_id": slot_id,
            "user_id": "customer_b",
            "joined_at": joined_b
        }
    )

    # 3. Register Customer A (joined 15 minutes ago - earlier)
    joined_a = (now - timedelta(minutes=15)).isoformat()
    client.post(
        "/api/v1/waitlist",
        json={
            "slot_id": slot_id,
            "user_id": "customer_a",
            "joined_at": joined_a
        }
    )

    # 4. View waitlist and verify ordering
    waitlist_res = client.get(f"/api/v1/slots/{slot_id}/waitlist")
    assert waitlist_res.status_code == 200
    entries = waitlist_res.json()
    assert len(entries) == 2
    
    # Earliest joined_at must be 1st
    assert entries[0]["user_id"] == "customer_a"
    assert entries[0]["priority_order"] == 1
    assert entries[1]["user_id"] == "customer_b"
    assert entries[1]["priority_order"] == 2
