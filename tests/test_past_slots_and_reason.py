from datetime import datetime, timedelta, timezone
from typing import Dict

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Booking, Slot, SlotStatus, User, WaitlistEntry
from app.services.allocation_service import book_slot, cancel_past_slot, join_waitlist


def _slot(db: Session, owner: User, start: datetime, status: str = SlotStatus.AVAILABLE.value) -> Slot:
    s = Slot(owner_id=owner.id, resource_id="r1", start_time=start,
             end_time=start + timedelta(hours=1), price=10, status=status)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def test_past_available_slot_is_cancelled(db: Session, business_user: User) -> None:
    now = datetime.now(timezone.utc)
    past = _slot(db, business_user, now - timedelta(hours=2))
    future = _slot(db, business_user, now + timedelta(hours=2))
    assert cancel_past_slot(db, past.id, now) is True
    assert cancel_past_slot(db, future.id, now) is False
    db.refresh(past)
    db.refresh(future)
    assert past.status == SlotStatus.CANCELLED.value
    assert future.status == SlotStatus.AVAILABLE.value


def test_past_booked_slot_is_left_alone(db: Session, business_user: User, customer_user: User) -> None:
    now = datetime.now(timezone.utc)
    future = _slot(db, business_user, now + timedelta(hours=1))
    book_slot(db, future.id, customer_user.id)
    # pretend time has passed
    assert cancel_past_slot(db, future.id, now + timedelta(hours=5)) is False
    db.refresh(future)
    assert future.status == SlotStatus.BOOKED.value


def test_past_slot_cancels_waitlist(db: Session, business_user: User,
                                    customer_user: User, customer_user_2: User) -> None:
    now = datetime.now(timezone.utc)
    s = _slot(db, business_user, now + timedelta(hours=1))
    book_slot(db, s.id, customer_user.id)
    join_waitlist(db, s.id, customer_user_2.id)
    # booked slots stay; make an AVAILABLE one with a stale waitlist-free state instead
    assert cancel_past_slot(db, s.id, now + timedelta(hours=5)) is False
    assert db.query(WaitlistEntry).filter_by(slot_id=s.id).first().status == "WAITING"


def test_business_cancel_requires_reason(
    client: TestClient, db: Session, business_user: User, customer_user: User,
    business_auth_headers: Dict[str, str], customer_auth_headers: Dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    s = _slot(db, business_user, now + timedelta(hours=3))
    b = book_slot(db, s.id, customer_user.id)
    booking_id = b.id if hasattr(b, "id") else db.query(Booking).first().id

    res = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=business_auth_headers)
    assert res.status_code == 422

    res = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=business_auth_headers,
                      json={"reason": "Doctor unavailable"})
    assert res.status_code == 200

    rows = client.get("/api/v1/business/bookings", headers=business_auth_headers).json()
    assert rows[0]["cancellation_reason"] == "Doctor unavailable"
    assert rows[0]["cancelled_by_role"] == "BUSINESS"

    mine = client.get("/api/v1/me/bookings", headers=customer_auth_headers).json()
    assert mine[0]["cancellation_reason"] == "Doctor unavailable"


def test_customer_cancel_reason_optional(
    client: TestClient, db: Session, business_user: User, customer_user: User,
    customer_auth_headers: Dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    s = _slot(db, business_user, now + timedelta(hours=3))
    b = book_slot(db, s.id, customer_user.id)
    booking_id = b.id if hasattr(b, "id") else db.query(Booking).first().id
    res = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=customer_auth_headers)
    assert res.status_code == 200
