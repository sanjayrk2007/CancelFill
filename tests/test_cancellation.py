from datetime import datetime, timezone, timedelta
from typing import Dict
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Slot, User

def test_cancellation_candidate_selection_flow(
    client: TestClient,
    db: Session,
    customer_user: User,
    business_auth_headers: Dict[str, str],
    customer_auth_headers: Dict[str, str],
    customer_2_auth_headers: Dict[str, str],
    other_customer_auth_headers: Dict[str, str],
    other_business_auth_headers: Dict[str, str]
) -> None:
    now = datetime.now(timezone.utc)

    slot_res = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "cancellation_test_slot",
            "start_time": (now + timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "price": "40.00"
        },
        headers=business_auth_headers
    )
    assert slot_res.status_code == 201
    slot_id = slot_res.json()["id"]

    booking_res = client.post(
        "/api/v1/bookings",
        json={"slot_id": slot_id},
        headers=other_customer_auth_headers
    )
    assert booking_res.status_code == 201
    booking_id = booking_res.json()["id"]

    client.post(
        "/api/v1/waitlist",
        json={
            "slot_id": slot_id,
            "joined_at": (now - timedelta(minutes=20)).isoformat()
        },
        headers=customer_auth_headers
    )
    client.post(
        "/api/v1/waitlist",
        json={
            "slot_id": slot_id,
            "joined_at": (now - timedelta(minutes=10)).isoformat()
        },
        headers=customer_2_auth_headers
    )

    res_no_auth = client.post(f"/api/v1/bookings/{booking_id}/cancel")
    assert res_no_auth.status_code == 401

    res_forbidden = client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        headers=customer_auth_headers
    )
    assert res_forbidden.status_code == 403

    res_other_biz = client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        headers=other_business_auth_headers
    )
    assert res_other_biz.status_code == 403

    cancel_res = client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        headers=other_customer_auth_headers
    )
    assert cancel_res.status_code == 200
    data = cancel_res.json()

    assert data["booking_id"] == booking_id
    assert data["booking_status"] == "CANCELLED"
    assert data["candidate_selected"] is True
    assert data["selected_user_id"] == customer_user.id
    assert data["slot_status"] == "HELD"
    assert data["hold"] is not None
    assert data["hold"]["user_id"] == customer_user.id
    assert data["hold"]["status"] == "ACTIVE"

    slot = db.query(Slot).filter(Slot.id == slot_id).one()
    assert slot.status == "HELD"

def test_slot_owner_can_cancel_booking(
    client: TestClient,
    business_auth_headers: Dict[str, str],
    customer_auth_headers: Dict[str, str]
) -> None:
    now = datetime.now(timezone.utc)
    slot_res = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "slot_owner_cancel_test",
            "start_time": (now + timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "price": "30.00"
        },
        headers=business_auth_headers
    )
    slot_id = slot_res.json()["id"]

    booking_res = client.post(
        "/api/v1/bookings",
        json={"slot_id": slot_id},
        headers=customer_auth_headers
    )
    booking_id = booking_res.json()["id"]

    cancel_res = client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        headers=business_auth_headers,
        json={"reason": "Owner cancelled"}
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["booking_status"] == "CANCELLED"
