from datetime import datetime, timezone, timedelta

def test_cancellation_candidate_selection_flow(client):
    now = datetime.now(timezone.utc)

    # 1. Create slot
    slot_res = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "cancellation_test_slot",
            "start_time": (now + timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat()
        }
    )
    slot_id = slot_res.json()["id"]

    # 2. Book slot for Charlie
    booking_res = client.post(
        "/api/v1/bookings",
        json={"slot_id": slot_id, "user_id": "user_charlie"}
    )
    booking_id = booking_res.json()["id"]

    # 3. Add Customer A (joined 20 mins ago) and Customer B (joined 10 mins ago)
    client.post(
        "/api/v1/waitlist",
        json={
            "slot_id": slot_id,
            "user_id": "customer_a",
            "joined_at": (now - timedelta(minutes=20)).isoformat()
        }
    )
    client.post(
        "/api/v1/waitlist",
        json={
            "slot_id": slot_id,
            "user_id": "customer_b",
            "joined_at": (now - timedelta(minutes=10)).isoformat()
        }
    )

    # 4. Cancel booking for Charlie
    cancel_res = client.post(f"/api/v1/bookings/{booking_id}/cancel")
    assert cancel_res.status_code == 200
    data = cancel_res.json()

    assert data["booking_id"] == booking_id
    assert data["booking_status"] == "CANCELLED"
    assert data["candidate_selected"] is True
    assert data["selected_user_id"] == "customer_a"
    assert data["slot_status"] == "HELD"
    assert data["hold"] is not None
    assert data["hold"]["user_id"] == "customer_a"
    assert data["hold"]["status"] == "ACTIVE"

    # 5. Verify slot status in DB via API
    slot_check = client.get(f"/api/v1/slots/{slot_id}")
    assert slot_check.json()["status"] == "HELD"
