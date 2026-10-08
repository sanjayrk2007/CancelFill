from datetime import datetime, timedelta, timezone
from typing import Dict

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Booking,
    BookingSource,
    BookingStatus,
    Hold,
    HoldStatus,
    Slot,
    SlotStatus,
    User,
    WaitlistEntry,
    WaitlistStatus,
)
from app.services.allocation_service import cancel_booking, decline_hold
from app.services.scheduler import expire_due_holds
from tests.conftest import TestingSessionLocal


def _slot(db: Session, owner: User, resource_id: str, status: str, now: datetime) -> Slot:
    slot = Slot(
        owner_id=owner.id,
        resource_id=resource_id,
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        price="50.00",
        status=status,
    )
    db.add(slot)
    db.flush()
    return slot


def test_expire_due_holds_cascades_without_sleep_and_is_idempotent(
    db: Session,
    monkeypatch,
    business_user: User,
    customer_user: User,
    customer_user_2: User,
    other_customer_user: User,
) -> None:
    monkeypatch.setattr("app.services.scheduler.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(settings, "DEFAULT_HOLD_DURATION_SECONDS", 30)
    now = datetime.now(timezone.utc)
    slot = _slot(db, business_user, "scheduler-cascade", SlotStatus.BOOKED.value, now)
    booking = Booking(
        slot_id=slot.id,
        user_id=customer_user.id,
        booked_at=now,
        status=BookingStatus.CONFIRMED.value,
        source=BookingSource.DIRECT.value,
    )
    candidates = [
        WaitlistEntry(slot_id=slot.id, user_id=customer_user_2.id, joined_at=now + timedelta(seconds=1), status=WaitlistStatus.WAITING.value),
        WaitlistEntry(slot_id=slot.id, user_id=other_customer_user.id, joined_at=now + timedelta(seconds=2), status=WaitlistStatus.WAITING.value),
        WaitlistEntry(slot_id=slot.id, user_id=customer_user.id, joined_at=now + timedelta(seconds=3), status=WaitlistStatus.WAITING.value),
    ]
    db.add_all([booking, *candidates])
    db.commit()

    cancel_booking(db=db, booking_id=booking.id, actor=customer_user.id, now=now)
    db.expire_all()
    first_hold = db.query(Hold).filter(Hold.slot_id == slot.id, Hold.user_id == customer_user_2.id).one()
    assert first_hold.status == HoldStatus.ACTIVE.value

    assert expire_due_holds(now=now + timedelta(seconds=31)) == 1
    db.expire_all()
    first_hold = db.query(Hold).filter(Hold.id == first_hold.id).one()
    second_hold = db.query(Hold).filter(Hold.slot_id == slot.id, Hold.user_id == other_customer_user.id).one()
    assert first_hold.status == HoldStatus.EXPIRED.value
    assert second_hold.status == HoldStatus.ACTIVE.value

    decline_hold(db=db, hold_id=second_hold.id, user_id=other_customer_user.id, now=now + timedelta(seconds=32))
    db.expire_all()
    third_hold = db.query(Hold).filter(Hold.slot_id == slot.id, Hold.user_id == customer_user.id).one()
    assert third_hold.status == HoldStatus.ACTIVE.value

    assert expire_due_holds(now=now + timedelta(seconds=63)) == 1
    assert expire_due_holds(now=now + timedelta(seconds=64)) == 0

    db.expire_all()
    slot = db.query(Slot).filter(Slot.id == slot.id).one()
    entries = db.query(WaitlistEntry).filter(WaitlistEntry.slot_id == slot.id).all()
    holds = db.query(Hold).filter(Hold.slot_id == slot.id).all()
    assert slot.status == SlotStatus.AVAILABLE.value
    assert sorted(entry.status for entry in entries) == sorted([
        WaitlistStatus.EXPIRED.value,
        WaitlistStatus.DECLINED.value,
        WaitlistStatus.EXPIRED.value,
    ])
    assert sorted(hold.status for hold in holds) == sorted([
        HoldStatus.EXPIRED.value,
        HoldStatus.DECLINED.value,
        HoldStatus.EXPIRED.value,
    ])


def test_me_endpoints_return_only_callers_data_and_lazy_expire_offers(
    client: TestClient,
    db: Session,
    business_user: User,
    customer_user: User,
    customer_user_2: User,
    other_customer_user: User,
    customer_auth_headers: Dict[str, str],
    customer_2_auth_headers: Dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    own_slot = _slot(db, business_user, "me-own", SlotStatus.HELD.value, now)
    overdue_slot = _slot(db, business_user, "me-overdue", SlotStatus.HELD.value, now)
    other_slot = _slot(db, business_user, "me-other", SlotStatus.HELD.value, now)
    booking_slot = _slot(db, business_user, "me-booking", SlotStatus.BOOKED.value, now)
    other_booking_slot = _slot(db, business_user, "me-other-booking", SlotStatus.BOOKED.value, now)
    waitlist_slot = _slot(db, business_user, "me-waitlist", SlotStatus.BOOKED.value, now)

    own_active_hold = Hold(
        slot_id=own_slot.id,
        user_id=customer_user.id,
        created_at=now,
        expires_at=now + timedelta(minutes=5),
        status=HoldStatus.ACTIVE.value,
    )
    own_overdue_hold = Hold(
        slot_id=overdue_slot.id,
        user_id=customer_user.id,
        created_at=now - timedelta(minutes=10),
        expires_at=now - timedelta(seconds=1),
        status=HoldStatus.ACTIVE.value,
    )
    other_hold = Hold(
        slot_id=other_slot.id,
        user_id=customer_user_2.id,
        created_at=now,
        expires_at=now + timedelta(minutes=5),
        status=HoldStatus.ACTIVE.value,
    )
    own_booking = Booking(
        slot_id=booking_slot.id,
        user_id=customer_user.id,
        booked_at=now,
        status=BookingStatus.CONFIRMED.value,
        source=BookingSource.DIRECT.value,
    )
    other_booking = Booking(
        slot_id=other_booking_slot.id,
        user_id=customer_user_2.id,
        booked_at=now,
        status=BookingStatus.CONFIRMED.value,
        source=BookingSource.DIRECT.value,
    )
    ahead = WaitlistEntry(slot_id=waitlist_slot.id, user_id=other_customer_user.id, joined_at=now, status=WaitlistStatus.WAITING.value)
    own_waitlist = WaitlistEntry(slot_id=waitlist_slot.id, user_id=customer_user.id, joined_at=now + timedelta(seconds=1), status=WaitlistStatus.WAITING.value)
    other_waitlist = WaitlistEntry(slot_id=waitlist_slot.id, user_id=customer_user_2.id, joined_at=now + timedelta(seconds=2), status=WaitlistStatus.WAITING.value)
    db.add_all([
        own_active_hold,
        own_overdue_hold,
        other_hold,
        own_booking,
        other_booking,
        ahead,
        own_waitlist,
        other_waitlist,
    ])
    db.commit()

    offers_response = client.get("/api/v1/me/offers", headers=customer_auth_headers)
    assert offers_response.status_code == 200
    offers = offers_response.json()
    assert [offer["id"] for offer in offers] == [own_active_hold.id]
    assert offers[0]["slot"]["id"] == own_slot.id
    assert offers[0]["seconds_remaining"] > 0
    db.refresh(own_overdue_hold)
    assert own_overdue_hold.status == HoldStatus.EXPIRED.value

    other_offers_response = client.get("/api/v1/me/offers", headers=customer_2_auth_headers)
    assert other_offers_response.status_code == 200
    assert [offer["id"] for offer in other_offers_response.json()] == [other_hold.id]

    bookings_response = client.get("/api/v1/me/bookings", headers=customer_auth_headers)
    assert bookings_response.status_code == 200
    bookings = bookings_response.json()
    assert [booking["id"] for booking in bookings] == [own_booking.id]
    assert bookings[0]["slot"]["id"] == booking_slot.id

    waitlist_response = client.get("/api/v1/me/waitlist", headers=customer_auth_headers)
    assert waitlist_response.status_code == 200
    waitlist_entries = waitlist_response.json()
    assert [entry["id"] for entry in waitlist_entries] == [own_waitlist.id]
    assert waitlist_entries[0]["priority_order"] == 2
    assert waitlist_entries[0]["slot"]["id"] == waitlist_slot.id