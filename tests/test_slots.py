from datetime import datetime, timezone, timedelta
from typing import Dict
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Slot

def test_create_and_get_slot(client: TestClient, db: Session, business_auth_headers: Dict[str, str]) -> None:
    now = datetime.now(timezone.utc)
    start_time = (now + timedelta(hours=1)).isoformat()
    end_time = (now + timedelta(hours=2)).isoformat()

    response = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "test_room_101",
            "start_time": start_time,
            "end_time": end_time,
            "price": "50.00"
        },
        headers=business_auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["resource_id"] == "test_room_101"
    assert data["status"] == "AVAILABLE"
    assert data["price"] == "50.00"
    assert "owner_id" in data
    slot_id = data["id"]

    list_response = client.get("/api/v1/slots")
    assert list_response.status_code == 200
    slots = list_response.json()
    assert len(slots) == 1
    assert slots[0]["id"] == slot_id

    slot = db.query(Slot).filter(Slot.id == slot_id).one()
    assert slot.id == slot_id

def test_create_slot_naive_datetime(client: TestClient, business_auth_headers: Dict[str, str]) -> None:
    response = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "room_naive_tz",
            "start_time": "2027-09-01T10:00:00",
            "end_time": "2027-09-01T11:00:00",
            "price": "25.50"
        },
        headers=business_auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["resource_id"] == "room_naive_tz"
    assert data["price"] == "25.50"

def test_create_slot_end_time_before_start_time(client: TestClient, business_auth_headers: Dict[str, str]) -> None:
    response = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "invalid_time_room",
            "start_time": "2027-09-01T12:00:00Z",
            "end_time": "2027-09-01T11:00:00Z",
            "price": "10.00"
        },
        headers=business_auth_headers
    )
    assert response.status_code == 422

def test_create_slot_auth_gates(
    client: TestClient,
    customer_auth_headers: Dict[str, str]
) -> None:
    payload = {
        "resource_id": "room_auth",
        "start_time": "2027-09-01T10:00:00Z",
        "end_time": "2027-09-01T11:00:00Z",
        "price": "10.00"
    }
    res_no_auth = client.post("/api/v1/slots", json=payload)
    assert res_no_auth.status_code == 401

    res_cust = client.post("/api/v1/slots", json=payload, headers=customer_auth_headers)
    assert res_cust.status_code == 403
