from datetime import datetime, timezone, timedelta

def test_create_and_get_slot(client):
    now = datetime.now(timezone.utc)
    start_time = (now + timedelta(hours=1)).isoformat()
    end_time = (now + timedelta(hours=2)).isoformat()

    # 1. Create Slot
    response = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "test_room_101",
            "start_time": start_time,
            "end_time": end_time
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["resource_id"] == "test_room_101"
    assert data["status"] == "AVAILABLE"
    slot_id = data["id"]

    # 2. Get Slot List
    list_response = client.get("/api/v1/slots")
    assert list_response.status_code == 200
    slots = list_response.json()
    assert len(slots) == 1
    assert slots[0]["id"] == slot_id

    # 3. Get Slot Detail
    detail_response = client.get(f"/api/v1/slots/{slot_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == slot_id
