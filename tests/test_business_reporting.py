from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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


def _slot(db: Session, owner: User, slot_id: str, resource_id: str, price: str, status: str, start: datetime) -> Slot:
    slot = Slot(
        id=slot_id,
        owner_id=owner.id,
        resource_id=resource_id,
        start_time=start,
        end_time=start + timedelta(hours=1),
        price=Decimal(price),
        status=status,
    )
    db.add(slot)
    return slot


def test_business_stats_match_hand_computed_fixture_and_other_business_sees_zeros(
    client: TestClient,
    db: Session,
    business_user: User,
    other_business_user: User,
    customer_user: User,
    customer_user_2: User,
    other_customer_user: User,
    business_auth_headers: Dict[str, str],
    other_business_auth_headers: Dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    slot_1 = _slot(db, business_user, "biz-slot-1", "room-a", "100.00", SlotStatus.BOOKED.value, now + timedelta(hours=1))
    slot_2 = _slot(db, business_user, "biz-slot-2", "room-b", "200.00", SlotStatus.BOOKED.value, now + timedelta(hours=2))
    slot_3 = _slot(db, business_user, "biz-slot-3", "room-c", "50.00", SlotStatus.HELD.value, now + timedelta(hours=3))
    slot_4 = _slot(db, business_user, "biz-slot-4", "room-d", "75.00", SlotStatus.AVAILABLE.value, now + timedelta(hours=4))

    rows = [
        Booking(id="cancelled-original", slot_id=slot_1.id, user_id=customer_user.id, booked_at=now, status=BookingStatus.CANCELLED.value, source=BookingSource.DIRECT.value),
        Booking(id="recovered-1", slot_id=slot_1.id, user_id=customer_user_2.id, booked_at=now + timedelta(minutes=1), status=BookingStatus.CONFIRMED.value, source=BookingSource.RECOVERED.value, recovered_from_booking_id="cancelled-original"),
        Booking(id="recovered-2", slot_id=slot_2.id, user_id=other_customer_user.id, booked_at=now + timedelta(minutes=2), status=BookingStatus.CONFIRMED.value, source=BookingSource.RECOVERED.value),
        Hold(id="accepted-offer", slot_id=slot_1.id, user_id=customer_user_2.id, created_at=now, expires_at=now + timedelta(minutes=15), status=HoldStatus.CONFIRMED.value),
        Hold(id="declined-offer", slot_id=slot_3.id, user_id=customer_user.id, created_at=now, expires_at=now + timedelta(minutes=15), status=HoldStatus.DECLINED.value),
        Hold(id="expired-offer", slot_id=slot_4.id, user_id=other_customer_user.id, created_at=now, expires_at=now - timedelta(minutes=1), status=HoldStatus.EXPIRED.value),
        WaitlistEntry(id="offered-entry", slot_id=slot_3.id, user_id=customer_user.id, joined_at=now, status=WaitlistStatus.OFFERED.value),
        WaitlistEntry(id="waiting-entry-1", slot_id=slot_3.id, user_id=customer_user_2.id, joined_at=now + timedelta(seconds=1), status=WaitlistStatus.WAITING.value),
        WaitlistEntry(id="waiting-entry-2", slot_id=slot_3.id, user_id=other_customer_user.id, joined_at=now + timedelta(seconds=2), status=WaitlistStatus.WAITING.value),
        WaitlistEntry(id="terminal-entry", slot_id=slot_3.id, user_id=customer_user.id, joined_at=now + timedelta(seconds=3), status=WaitlistStatus.EXPIRED.value),
    ]
    db.add_all(rows)
    db.commit()

    stats_response = client.get("/api/v1/business/stats", headers=business_auth_headers)
    assert stats_response.status_code == 200
    assert stats_response.json() == {
        "total_slots": 4,
        "booked_slots": 2,
        "utilization_rate": 0.5,
        "cancellations": 1,
        "offers_made": 3,
        "offers_accepted": 1,
        "offers_declined": 1,
        "offers_expired": 1,
        "conversion_rate": 1 / 3,
        "recovered_bookings": 2,
        "recovered_revenue": "300.00",
    }

    other_stats_response = client.get("/api/v1/business/stats", headers=other_business_auth_headers)
    assert other_stats_response.status_code == 200
    assert other_stats_response.json() == {
        "total_slots": 0,
        "booked_slots": 0,
        "utilization_rate": 0.0,
        "cancellations": 0,
        "offers_made": 0,
        "offers_accepted": 0,
        "offers_declined": 0,
        "offers_expired": 0,
        "conversion_rate": 0.0,
        "recovered_bookings": 0,
        "recovered_revenue": "0.00",
    }


def test_business_views_are_scoped_and_include_aggregate_details(
    client: TestClient,
    db: Session,
    business_user: User,
    other_business_user: User,
    customer_user: User,
    customer_user_2: User,
    other_customer_user: User,
    business_auth_headers: Dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    slot_1 = _slot(db, business_user, "view-slot-1", "view-a", "100.00", SlotStatus.BOOKED.value, now + timedelta(hours=1))
    slot_2 = _slot(db, business_user, "view-slot-2", "view-b", "50.00", SlotStatus.HELD.value, now + timedelta(hours=2))
    other_slot = _slot(db, other_business_user, "view-other-slot", "other", "500.00", SlotStatus.BOOKED.value, now + timedelta(hours=3))
    db.add_all([
        Booking(id="view-booking-active", slot_id=slot_1.id, user_id=customer_user.id, booked_at=now, status=BookingStatus.CONFIRMED.value, source=BookingSource.DIRECT.value),
        Booking(id="view-booking-cancelled", slot_id=slot_1.id, user_id=customer_user_2.id, booked_at=now - timedelta(minutes=5), status=BookingStatus.CANCELLED.value, source=BookingSource.DIRECT.value),
        Booking(id="view-other-booking", slot_id=other_slot.id, user_id=other_customer_user.id, booked_at=now, status=BookingStatus.CONFIRMED.value, source=BookingSource.DIRECT.value),
        Hold(id="view-active-hold", slot_id=slot_2.id, user_id=customer_user_2.id, created_at=now, expires_at=now + timedelta(minutes=10), status=HoldStatus.ACTIVE.value),
        WaitlistEntry(id="view-offered", slot_id=slot_2.id, user_id=customer_user_2.id, joined_at=now, status=WaitlistStatus.OFFERED.value),
        WaitlistEntry(id="view-waiting-1", slot_id=slot_2.id, user_id=customer_user.id, joined_at=now + timedelta(seconds=1), status=WaitlistStatus.WAITING.value),
        WaitlistEntry(id="view-waiting-2", slot_id=slot_2.id, user_id=other_customer_user.id, joined_at=now + timedelta(seconds=2), status=WaitlistStatus.WAITING.value),
        WaitlistEntry(id="view-other-waiting", slot_id=other_slot.id, user_id=customer_user.id, joined_at=now, status=WaitlistStatus.WAITING.value),
    ])
    db.commit()

    slots_response = client.get("/api/v1/business/slots", headers=business_auth_headers)
    assert slots_response.status_code == 200
    slots = slots_response.json()
    assert [slot["id"] for slot in slots] == [slot_1.id, slot_2.id]
    assert slots[0]["active_booking_id"] == "view-booking-active"
    assert slots[0]["active_booking_holder_name"] == customer_user.name
    assert slots[1]["waitlist_count"] == 3
    assert slots[1]["active_hold_holder_name"] == customer_user_2.name
    assert slots[1]["active_hold_expires_at"] is not None

    waitlist_response = client.get("/api/v1/business/waitlist", headers=business_auth_headers)
    assert waitlist_response.status_code == 200
    waitlist = waitlist_response.json()
    assert len(waitlist) == 1
    assert waitlist[0]["slot_id"] == slot_2.id
    assert [entry["id"] for entry in waitlist[0]["entries"]] == ["view-offered", "view-waiting-1", "view-waiting-2"]
    assert [entry["position"] for entry in waitlist[0]["entries"]] == [None, 1, 2]

    bookings_response = client.get("/api/v1/business/bookings", headers=business_auth_headers)
    assert bookings_response.status_code == 200
    assert {booking["id"] for booking in bookings_response.json()} == {"view-booking-active", "view-booking-cancelled"}

    confirmed_response = client.get("/api/v1/business/bookings?status=CONFIRMED", headers=business_auth_headers)
    assert confirmed_response.status_code == 200
    assert [booking["id"] for booking in confirmed_response.json()] == ["view-booking-active"]