from datetime import datetime, timezone, timedelta
from typing import Dict
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models import (
    Slot,
    SlotStatus,
    Hold,
    HoldStatus,
    WaitlistEntry,
    WaitlistStatus,
    Booking,
    BookingStatus,
    BookingSource,
    User,
)
from app.services.state_machine import (
    assert_transition,
    InvalidTransition,
)
from tests.invariants import assert_invariants

def test_state_machine_slot_transitions() -> None:
    assert_transition("Slot", "AVAILABLE", "BOOKED")
    assert_transition("Slot", "BOOKED", "AVAILABLE")
    assert_transition("Slot", "AVAILABLE", "HELD")
    assert_transition("Slot", "HELD", "BOOKED")
    assert_transition("Slot", "HELD", "AVAILABLE")

    with pytest.raises(InvalidTransition):
        assert_transition("Slot", "AVAILABLE", "AVAILABLE")
    with pytest.raises(InvalidTransition):
        assert_transition("Slot", "BOOKED", "HELD")
    with pytest.raises(InvalidTransition):
        assert_transition("Slot", "HELD", "HELD")
    with pytest.raises(InvalidTransition):
        assert_transition("Slot", "BOOKED", "BOOKED")

def test_state_machine_hold_transitions() -> None:
    assert_transition("Hold", "ACTIVE", "CONFIRMED")
    assert_transition("Hold", "ACTIVE", "EXPIRED")
    assert_transition("Hold", "ACTIVE", "DECLINED")

    with pytest.raises(InvalidTransition):
        assert_transition("Hold", "CONFIRMED", "ACTIVE")
    with pytest.raises(InvalidTransition):
        assert_transition("Hold", "EXPIRED", "ACTIVE")
    with pytest.raises(InvalidTransition):
        assert_transition("Hold", "DECLINED", "ACTIVE")
    with pytest.raises(InvalidTransition):
        assert_transition("Hold", "CONFIRMED", "EXPIRED")

def test_state_machine_waitlist_transitions() -> None:
    assert_transition("WaitlistEntry", "WAITING", "OFFERED")
    assert_transition("WaitlistEntry", "WAITING", "CANCELLED")
    assert_transition("WaitlistEntry", "OFFERED", "CONFIRMED")
    assert_transition("WaitlistEntry", "OFFERED", "DECLINED")
    assert_transition("WaitlistEntry", "OFFERED", "EXPIRED")

    with pytest.raises(InvalidTransition):
        assert_transition("WaitlistEntry", "WAITING", "CONFIRMED")
    with pytest.raises(InvalidTransition):
        assert_transition("WaitlistEntry", "OFFERED", "CANCELLED")
    with pytest.raises(InvalidTransition):
        assert_transition("WaitlistEntry", "CONFIRMED", "WAITING")
    with pytest.raises(InvalidTransition):
        assert_transition("WaitlistEntry", "CANCELLED", "WAITING")

def test_state_machine_booking_transitions() -> None:
    assert_transition("Booking", "CONFIRMED", "CANCELLED")

    with pytest.raises(InvalidTransition):
        assert_transition("Booking", "CANCELLED", "CONFIRMED")
    with pytest.raises(InvalidTransition):
        assert_transition("Booking", "CONFIRMED", "CONFIRMED")
    with pytest.raises(InvalidTransition):
        assert_transition("Booking", "CANCELLED", "CANCELLED")

def test_accept_hold_by_wrong_user(
    client: TestClient,
    db: Session,
    business_auth_headers: Dict[str, str],
    customer_auth_headers: Dict[str, str],
    customer_2_auth_headers: Dict[str, str]
) -> None:
    now = datetime.now(timezone.utc)
    slot_res = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "wrong_user_test",
            "start_time": (now + timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "price": "50.00"
        },
        headers=business_auth_headers
    )
    slot_id = slot_res.json()["id"]

    client.post("/api/v1/bookings", json={"slot_id": slot_id}, headers=customer_auth_headers)
    client.post("/api/v1/waitlist", json={"slot_id": slot_id}, headers=customer_2_auth_headers)

    booking = db.query(Booking).filter(Booking.slot_id == slot_id, Booking.status == BookingStatus.CONFIRMED.value).one()
    booking_id = booking.id

    cancel_res = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=customer_auth_headers)
    hold_id = cancel_res.json()["hold"]["id"]

    accept_wrong = client.post(f"/api/v1/holds/{hold_id}/accept", headers=customer_auth_headers)
    assert accept_wrong.status_code == 403

def test_accept_hold_twice(
    client: TestClient,
    db: Session,
    business_auth_headers: Dict[str, str],
    customer_auth_headers: Dict[str, str],
    customer_2_auth_headers: Dict[str, str]
) -> None:
    now = datetime.now(timezone.utc)
    slot_res = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "accept_twice_test",
            "start_time": (now + timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "price": "50.00"
        },
        headers=business_auth_headers
    )
    slot_id = slot_res.json()["id"]

    client.post("/api/v1/bookings", json={"slot_id": slot_id}, headers=customer_auth_headers)
    client.post("/api/v1/waitlist", json={"slot_id": slot_id}, headers=customer_2_auth_headers)

    booking = db.query(Booking).filter(Booking.slot_id == slot_id, Booking.status == BookingStatus.CONFIRMED.value).one()
    booking_id = booking.id

    cancel_res = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=customer_auth_headers)
    hold_id = cancel_res.json()["hold"]["id"]

    accept_1 = client.post(f"/api/v1/holds/{hold_id}/accept", headers=customer_2_auth_headers)
    assert accept_1.status_code == 200
    assert accept_1.json()["source"] == "RECOVERED"
    assert accept_1.json()["recovered_from_booking_id"] == booking_id

    accept_2 = client.post(f"/api/v1/holds/{hold_id}/accept", headers=customer_2_auth_headers)
    assert accept_2.status_code == 409
    assert accept_2.json()["detail"] == "This offer is no longer available"

def test_direct_booking_held_slot_returns_409_and_preserves_active_hold(
    client: TestClient,
    db: Session,
    business_user: User,
    customer_user: User,
    customer_user_2: User,
    customer_2_auth_headers: Dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    slot = Slot(
        owner_id=business_user.id,
        resource_id="held_direct_booking_guard",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        price="50.00",
        status=SlotStatus.HELD.value,
    )
    hold = Hold(
        slot=slot,
        user_id=customer_user.id,
        expires_at=now + timedelta(minutes=15),
        status=HoldStatus.ACTIVE.value,
    )
    db.add_all([slot, hold])
    db.commit()

    res = client.post("/api/v1/bookings", json={"slot_id": slot.id}, headers=customer_2_auth_headers)
    assert res.status_code == 409

    db.expire_all()
    slot = db.query(Slot).filter(Slot.id == slot.id).one()
    hold = db.query(Hold).filter(Hold.id == hold.id).one()
    assert slot.status == SlotStatus.HELD.value
    assert hold.status == HoldStatus.ACTIVE.value
    assert_invariants(db)

def test_direct_booking_booked_slot_returns_409_and_preserves_booking(
    client: TestClient,
    db: Session,
    business_user: User,
    customer_user: User,
    customer_user_2: User,
    customer_2_auth_headers: Dict[str, str],
) -> None:
    now = datetime.now(timezone.utc)
    slot = Slot(
        owner_id=business_user.id,
        resource_id="booked_direct_booking_guard",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        price="50.00",
        status=SlotStatus.BOOKED.value,
    )
    booking = Booking(
        slot=slot,
        user_id=customer_user.id,
        booked_at=now,
        status=BookingStatus.CONFIRMED.value,
        source=BookingSource.DIRECT.value,
    )
    db.add_all([slot, booking])
    db.commit()

    res = client.post("/api/v1/bookings", json={"slot_id": slot.id}, headers=customer_2_auth_headers)
    assert res.status_code == 409

    db.expire_all()
    slot = db.query(Slot).filter(Slot.id == slot.id).one()
    booking = db.query(Booking).filter(Booking.id == booking.id).one()
    assert slot.status == SlotStatus.BOOKED.value
    assert booking.status == BookingStatus.CONFIRMED.value
    assert_invariants(db)

def test_accept_after_expiry_cascades_to_next_candidate(
    client: TestClient,
    db: Session,
    business_auth_headers: Dict[str, str],
    customer_auth_headers: Dict[str, str],
    customer_2_auth_headers: Dict[str, str],
    other_customer_auth_headers: Dict[str, str],
    other_customer_user: User
) -> None:
    now = datetime.now(timezone.utc)
    slot_res = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "expiry_cascade_test",
            "start_time": (now + timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "price": "50.00"
        },
        headers=business_auth_headers
    )
    slot_id = slot_res.json()["id"]

    client.post("/api/v1/bookings", json={"slot_id": slot_id}, headers=customer_auth_headers)

    client.post(
        "/api/v1/waitlist",
        json={"slot_id": slot_id, "joined_at": (now - timedelta(minutes=10)).isoformat()},
        headers=customer_2_auth_headers
    )
    client.post(
        "/api/v1/waitlist",
        json={"slot_id": slot_id, "joined_at": (now - timedelta(minutes=5)).isoformat()},
        headers=other_customer_auth_headers
    )

    booking = db.query(Booking).filter(Booking.slot_id == slot_id, Booking.status == BookingStatus.CONFIRMED.value).one()
    booking_id = booking.id

    cancel_res = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=customer_auth_headers)
    hold_id = cancel_res.json()["hold"]["id"]

    hold_row = db.query(Hold).filter(Hold.id == hold_id).first()
    assert hold_row is not None
    hold_row.expires_at = now - timedelta(minutes=1)
    db.commit()

    accept_res = client.post(f"/api/v1/holds/{hold_id}/accept", headers=customer_2_auth_headers)
    assert accept_res.status_code == 409
    assert accept_res.json()["detail"] == "This offer is no longer available"

    db.refresh(hold_row)
    assert hold_row.status == "EXPIRED"

    next_hold = db.query(Hold).filter(Hold.slot_id == slot_id, Hold.status == "ACTIVE").first()
    assert next_hold is not None
    assert next_hold.user_id == other_customer_user.id

    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    assert slot is not None
    assert slot.status == "HELD"

def test_decline_cascades(
    client: TestClient,
    db: Session,
    business_auth_headers: Dict[str, str],
    customer_auth_headers: Dict[str, str],
    customer_2_auth_headers: Dict[str, str],
    other_customer_auth_headers: Dict[str, str],
    other_customer_user: User
) -> None:
    now = datetime.now(timezone.utc)
    slot_res = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "decline_cascade_test",
            "start_time": (now + timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "price": "50.00"
        },
        headers=business_auth_headers
    )
    slot_id = slot_res.json()["id"]

    client.post("/api/v1/bookings", json={"slot_id": slot_id}, headers=customer_auth_headers)

    client.post(
        "/api/v1/waitlist",
        json={"slot_id": slot_id, "joined_at": (now - timedelta(minutes=10)).isoformat()},
        headers=customer_2_auth_headers
    )
    client.post(
        "/api/v1/waitlist",
        json={"slot_id": slot_id, "joined_at": (now - timedelta(minutes=5)).isoformat()},
        headers=other_customer_auth_headers
    )

    booking = db.query(Booking).filter(Booking.slot_id == slot_id, Booking.status == BookingStatus.CONFIRMED.value).one()
    booking_id = booking.id

    cancel_res = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=customer_auth_headers)
    hold_id = cancel_res.json()["hold"]["id"]

    decline_1 = client.post(f"/api/v1/holds/{hold_id}/decline", headers=customer_2_auth_headers)
    assert decline_1.status_code == 200
    assert decline_1.json()["status"] == "DECLINED"

    next_hold = db.query(Hold).filter(Hold.slot_id == slot_id, Hold.status == "ACTIVE").first()
    assert next_hold is not None
    assert next_hold.user_id == other_customer_user.id

    decline_2 = client.post(f"/api/v1/holds/{next_hold.id}/decline", headers=other_customer_auth_headers)
    assert decline_2.status_code == 200
    assert decline_2.json()["status"] == "DECLINED"

    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    assert slot is not None
    assert slot.status == "AVAILABLE"

def test_double_cancel(
    client: TestClient,
    db: Session,
    business_auth_headers: Dict[str, str],
    customer_auth_headers: Dict[str, str]
) -> None:
    now = datetime.now(timezone.utc)
    slot_res = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "double_cancel_test",
            "start_time": (now + timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "price": "50.00"
        },
        headers=business_auth_headers
    )
    slot_id = slot_res.json()["id"]

    client.post("/api/v1/bookings", json={"slot_id": slot_id}, headers=customer_auth_headers)
    booking = db.query(Booking).filter(Booking.slot_id == slot_id, Booking.status == BookingStatus.CONFIRMED.value).one()
    booking_id = booking.id

    cancel_1 = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=customer_auth_headers)
    assert cancel_1.status_code == 200

    cancel_2 = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=customer_auth_headers)
    assert cancel_2.status_code == 409

def test_waitlist_rule_violations(
    client: TestClient,
    business_auth_headers: Dict[str, str],
    customer_auth_headers: Dict[str, str],
    customer_2_auth_headers: Dict[str, str]
) -> None:
    now = datetime.now(timezone.utc)
    slot_res = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "waitlist_rules_test",
            "start_time": (now + timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=2)).isoformat(),
            "price": "50.00"
        },
        headers=business_auth_headers
    )
    slot_id = slot_res.json()["id"]

    res_avail = client.post("/api/v1/waitlist", json={"slot_id": slot_id}, headers=customer_auth_headers)
    assert res_avail.status_code == 409

    client.post("/api/v1/bookings", json={"slot_id": slot_id}, headers=customer_auth_headers)

    res_holder = client.post("/api/v1/waitlist", json={"slot_id": slot_id}, headers=customer_auth_headers)
    assert res_holder.status_code == 409

    res_join = client.post("/api/v1/waitlist", json={"slot_id": slot_id}, headers=customer_2_auth_headers)
    assert res_join.status_code == 201
    waitlist_id = res_join.json()["id"]

    res_dup = client.post("/api/v1/waitlist", json={"slot_id": slot_id}, headers=customer_2_auth_headers)
    assert res_dup.status_code == 409

    del_wrong = client.delete(f"/api/v1/waitlist/{waitlist_id}", headers=customer_auth_headers)
    assert del_wrong.status_code == 403

    del_ok = client.delete(f"/api/v1/waitlist/{waitlist_id}", headers=customer_2_auth_headers)
    assert del_ok.status_code == 200
    assert del_ok.json()["status"] == "CANCELLED"

    del_again = client.delete(f"/api/v1/waitlist/{waitlist_id}", headers=customer_2_auth_headers)
    assert del_again.status_code == 409

def test_full_cycle_api(
    client: TestClient,
    db: Session,
    business_auth_headers: Dict[str, str],
    customer_auth_headers: Dict[str, str],
    customer_2_auth_headers: Dict[str, str],
    other_customer_auth_headers: Dict[str, str],
    customer_user_2: User
) -> None:
    now = datetime.now(timezone.utc)

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "cust4@example.com",
            "name": "Customer Four",
            "password": "password123",
            "role": "CUSTOMER"
        }
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "cust4@example.com", "password": "password123"}
    )
    cust4_token = login_res.json()["access_token"]
    cust4_headers = {"Authorization": f"Bearer {cust4_token}"}

    slot_res = client.post(
        "/api/v1/slots",
        json={
            "resource_id": "full_cycle_slot",
            "start_time": (now + timedelta(hours=2)).isoformat(),
            "end_time": (now + timedelta(hours=3)).isoformat(),
            "price": "99.00"
        },
        headers=business_auth_headers
    )
    assert slot_res.status_code == 201
    slot_id = slot_res.json()["id"]

    book_res = client.post(
        "/api/v1/bookings",
        json={"slot_id": slot_id},
        headers=customer_auth_headers
    )
    assert book_res.status_code == 201
    first_booking_id = book_res.json()["id"]
    assert book_res.json()["source"] == "DIRECT"

    w1 = client.post(
        "/api/v1/waitlist",
        json={"slot_id": slot_id, "joined_at": (now - timedelta(minutes=30)).isoformat()},
        headers=customer_2_auth_headers
    )
    assert w1.status_code == 201

    w2 = client.post(
        "/api/v1/waitlist",
        json={"slot_id": slot_id, "joined_at": (now - timedelta(minutes=20)).isoformat()},
        headers=other_customer_auth_headers
    )
    assert w2.status_code == 201

    w3 = client.post(
        "/api/v1/waitlist",
        json={"slot_id": slot_id, "joined_at": (now - timedelta(minutes=10)).isoformat()},
        headers=cust4_headers
    )
    assert w3.status_code == 201

    cancel_res = client.post(
        f"/api/v1/bookings/{first_booking_id}/cancel",
        headers=customer_auth_headers
    )
    assert cancel_res.status_code == 200
    cancel_data = cancel_res.json()
    assert cancel_data["candidate_selected"] is True
    assert cancel_data["selected_user_id"] == customer_user_2.id
    hold_id = cancel_data["hold"]["id"]

    accept_res = client.post(
        f"/api/v1/holds/{hold_id}/accept",
        headers=customer_2_auth_headers
    )
    assert accept_res.status_code == 200
    recovered_booking = accept_res.json()
    assert recovered_booking["status"] == "CONFIRMED"
    assert recovered_booking["source"] == "RECOVERED"
    assert recovered_booking["recovered_from_booking_id"] == first_booking_id
    assert recovered_booking["user_id"] == customer_user_2.id

    slot = db.query(Slot).filter(Slot.id == slot_id).one()
    assert slot.status == "BOOKED"

def test_db_partial_unique_index_guards(
    db: Session,
    business_user: User,
    customer_user: User,
    customer_user_2: User
) -> None:
    now = datetime.now(timezone.utc)
    slot = Slot(
        owner_id=business_user.id,
        resource_id="guard_test_slot",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        price=10.0,
        status=SlotStatus.AVAILABLE.value
    )
    db.add(slot)
    db.commit()

    hold1 = Hold(
        slot_id=slot.id,
        user_id=customer_user.id,
        created_at=now,
        expires_at=now + timedelta(minutes=10),
        status=HoldStatus.ACTIVE.value
    )
    db.add(hold1)
    db.commit()

    hold2 = Hold(
        slot_id=slot.id,
        user_id=customer_user_2.id,
        created_at=now,
        expires_at=now + timedelta(minutes=10),
        status=HoldStatus.ACTIVE.value
    )
    db.add(hold2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    b1 = Booking(
        slot_id=slot.id,
        user_id=customer_user.id,
        booked_at=now,
        status=BookingStatus.CONFIRMED.value,
        source=BookingSource.DIRECT.value
    )
    db.add(b1)
    db.commit()

    b2 = Booking(
        slot_id=slot.id,
        user_id=customer_user_2.id,
        booked_at=now,
        status=BookingStatus.CONFIRMED.value,
        source=BookingSource.DIRECT.value
    )
    db.add(b2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    w1 = WaitlistEntry(
        slot_id=slot.id,
        user_id=customer_user.id,
        joined_at=now,
        status=WaitlistStatus.WAITING.value
    )
    db.add(w1)
    db.commit()

    w2 = WaitlistEntry(
        slot_id=slot.id,
        user_id=customer_user.id,
        joined_at=now + timedelta(seconds=5),
        status=WaitlistStatus.OFFERED.value
    )
    db.add(w2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
