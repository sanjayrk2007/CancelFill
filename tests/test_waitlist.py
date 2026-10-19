from datetime import datetime, timezone, timedelta
from typing import Dict
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import User, WaitlistEntry
from app.services.allocation_service import join_waitlist

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

    entry_b = join_waitlist(db=db, slot_id=slot_id, user_id=customer_user_2.id, joined_at=now - timedelta(minutes=5))
    assert entry_b.user_id == customer_user_2.id

    entry_a = join_waitlist(db=db, slot_id=slot_id, user_id=customer_user.id, joined_at=now - timedelta(minutes=15))
    assert entry_a.user_id == customer_user.id

    entries = db.query(WaitlistEntry).filter(WaitlistEntry.slot_id == slot_id).order_by(WaitlistEntry.joined_at.asc()).all()
    assert len(entries) == 2
    
    assert entries[0].user_id == customer_user.id
    assert entries[1].user_id == customer_user_2.id

def test_spoofed_joined_at_ignored(
    client: TestClient,
    db: Session,
    customer_user: User,
    business_auth_headers: Dict[str, str],
    customer_auth_headers: Dict[str, str],
    other_customer_auth_headers: Dict[str, str]
) -> None:
    now = datetime.now(timezone.utc)
    slot_res = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "test_spoof_slot",
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

    spoofed_time = (now - timedelta(days=365)).isoformat()
    res = client.post(
        "/api/v1/waitlist",
        json={
            "slot_id": slot_id,
            "joined_at": spoofed_time
        },
        headers=customer_auth_headers
    )
    assert res.status_code == 201
    data = res.json()
    assert data["user_id"] == customer_user.id
    joined_at_val = datetime.fromisoformat(data["joined_at"])
    if joined_at_val.tzinfo is None:
        joined_at_val = joined_at_val.replace(tzinfo=timezone.utc)
    assert joined_at_val > now - timedelta(minutes=1)

    db_entry = db.query(WaitlistEntry).filter(WaitlistEntry.slot_id == slot_id, WaitlistEntry.user_id == customer_user.id).first()
    assert db_entry is not None
    db_joined = db_entry.joined_at
    if db_joined.tzinfo is None:
        db_joined = db_joined.replace(tzinfo=timezone.utc)
    assert db_joined > now - timedelta(minutes=1)

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
