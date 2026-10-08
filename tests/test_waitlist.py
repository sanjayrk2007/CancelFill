from datetime import datetime, timezone, timedelta
from typing import Dict
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import User, WaitlistEntry

def test_waitlist_registration_and_priority(
    client: TestClient,
    db: Session,
    customer_user: User,
    customer_user_2: User,
    business_auth_headers: Dict[str, str],
    customer_auth_headers: Dict[str, str],
    customer_2_auth_headers: Dict[str, str],
    other_customer_auth_headers: Dict[str, str]
) -> None:
    now = datetime.now(timezone.utc)
    
    slot_res = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "test_service_slot",
            "start_time": (now + timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "price": "50.00"
        },
        headers=business_auth_headers
    )
    assert slot_res.status_code == 201
    slot_id = slot_res.json()["id"]

    book_res = client.post(
        "/api/v1/bookings",
        json={"slot_id": slot_id},
        headers=other_customer_auth_headers
    )
    assert book_res.status_code == 201

    joined_b = (now - timedelta(minutes=5)).isoformat()
    res_b = client.post(
        "/api/v1/waitlist",
        json={
            "slot_id": slot_id,
            "joined_at": joined_b
        },
        headers=customer_2_auth_headers
    )
    assert res_b.status_code == 201
    assert res_b.json()["user_id"] == customer_user_2.id

    joined_a = (now - timedelta(minutes=15)).isoformat()
    res_a = client.post(
        "/api/v1/waitlist",
        json={
            "slot_id": slot_id,
            "joined_at": joined_a
        },
        headers=customer_auth_headers
    )
    assert res_a.status_code == 201
    assert res_a.json()["user_id"] == customer_user.id

    entries = db.query(WaitlistEntry).filter(WaitlistEntry.slot_id == slot_id).order_by(WaitlistEntry.joined_at.asc()).all()
    assert len(entries) == 2
    
    assert entries[0].user_id == customer_user.id
    assert entries[1].user_id == customer_user_2.id

def test_waitlist_auth_gates(
    client: TestClient,
    business_auth_headers: Dict[str, str]
) -> None:
    res_no_auth = client.post(
        "/api/v1/waitlist",
        json={"slot_id": "slot-123"}
    )
    assert res_no_auth.status_code == 401

    res_biz = client.post(
        "/api/v1/waitlist",
        json={"slot_id": "slot-123"},
        headers=business_auth_headers
    )
    assert res_biz.status_code == 403
