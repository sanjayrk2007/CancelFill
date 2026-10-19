"""SRS 3.2: FR-06 (capacity), FR-07 (edit), FR-08 (remove), NFR-03, NFR-06."""
from datetime import datetime, timedelta, timezone
from typing import Dict

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus, Hold, HoldStatus, Notification, Slot, SlotStatus, User
from tests.helpers import make_slot
from tests.invariants import assert_invariants


def _book(client: TestClient, headers: Dict[str, str], slot_id: str):
    return client.post("/api/v1/bookings", json={"slot_id": slot_id}, headers=headers)


# ---------------------------------------------------------------- FR-06 capacity is an attribute

def test_create_slot_with_capacity_and_default(client: TestClient, business_auth_headers: Dict[str, str]) -> None:
    base = {"resource_id": "court", "start_time": "2030-01-01T10:00:00Z", "end_time": "2030-01-01T11:00:00Z"}
    r = client.post("/api/v1/slots", json={**base, "capacity": 12}, headers=business_auth_headers)
    assert r.status_code == 201 and r.json()["capacity"] == 12
    assert client.post("/api/v1/slots", json=base, headers=business_auth_headers).json()["capacity"] == 1
    assert client.post("/api/v1/slots", json={**base, "capacity": 0}, headers=business_auth_headers).status_code == 422


def test_capacity_never_allows_a_second_booking_or_hold(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_user_2: User,
    customer_auth_headers, customer_2_auth_headers,
) -> None:
    """NFR-03: a slot confirms for exactly one customer, whatever its capacity says."""
    slot = make_slot(db, business_user, capacity=20)
    assert _book(client, customer_auth_headers, slot.id).status_code == 201
    assert _book(client, customer_2_auth_headers, slot.id).status_code == 409
    db.refresh(slot)
    assert slot.status == SlotStatus.BOOKED.value
    assert client.post("/api/v1/waitlist", json={"slot_id": slot.id}, headers=customer_2_auth_headers).status_code == 201
    assert db.query(Booking).filter(Booking.status == BookingStatus.CONFIRMED.value).count() == 1
    assert_invariants(db)


# ---------------------------------------------------------------- FR-07 edit

def test_edit_available_slot(
    client: TestClient, db: Session, business_user: User, business_auth_headers
) -> None:
    slot = make_slot(db, business_user, price="10.00")
    new_start = (datetime.now(timezone.utc) + timedelta(days=5)).replace(microsecond=0)
    r = client.patch(
        f"/api/v1/slots/{slot.id}",
        json={"resource_id": "renamed", "price": "99.50", "capacity": 6,
              "start_time": new_start.isoformat(), "end_time": (new_start + timedelta(hours=2)).isoformat()},
        headers=business_auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert (body["resource_id"], body["price"], body["capacity"], body["status"]) == ("renamed", "99.50", 6, "AVAILABLE")
    assert client.get("/api/v1/business/slots", headers=business_auth_headers).json()[0]["resource_id"] == "renamed"


def test_edit_booked_slot_is_rejected_with_explanation(
    client: TestClient, db: Session, business_user: User, customer_user: User,
    customer_auth_headers, business_auth_headers,
) -> None:
    slot = make_slot(db, business_user, price="10.00")
    _book(client, customer_auth_headers, slot.id)
    r = client.patch(f"/api/v1/slots/{slot.id}", json={"price": "999"}, headers=business_auth_headers)
    assert r.status_code == 409
    assert "booked" in r.json()["detail"].lower() and "cancel the booking" in r.json()["detail"].lower()
    db.refresh(slot)
    assert float(slot.price) == 10.0  # nothing changed


def test_edit_held_slot_is_rejected_with_explanation(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_user_2: User,
    customer_auth_headers, customer_2_auth_headers, business_auth_headers,
) -> None:
    slot = make_slot(db, business_user)
    b = _book(client, customer_auth_headers, slot.id).json()
    client.post("/api/v1/waitlist", json={"slot_id": slot.id}, headers=customer_2_auth_headers)
    client.post(f"/api/v1/bookings/{b['id']}/cancel", headers=customer_auth_headers)  # offer -> HELD
    db.refresh(slot)
    assert slot.status == SlotStatus.HELD.value
    r = client.patch(f"/api/v1/slots/{slot.id}", json={"price": "5"}, headers=business_auth_headers)
    assert r.status_code == 409 and "held" in r.json()["detail"].lower()
    assert client.delete(f"/api/v1/slots/{slot.id}", headers=business_auth_headers).status_code == 409
    assert db.query(Hold).filter(Hold.slot_id == slot.id, Hold.status == HoldStatus.ACTIVE.value).count() == 1


def test_edit_validation_and_authorization(
    client: TestClient, db: Session, business_user: User, other_business_user: User,
    business_auth_headers, other_business_auth_headers, customer_auth_headers,
) -> None:
    slot = make_slot(db, business_user)
    url = f"/api/v1/slots/{slot.id}"
    assert client.patch(url, json={}, headers=business_auth_headers).status_code == 422
    assert client.patch(url, json={"price": "-1"}, headers=business_auth_headers).status_code == 422
    assert client.patch(url, json={"capacity": 0}, headers=business_auth_headers).status_code == 422
    assert client.patch(url, json={"end_time": (slot.start_time - timedelta(hours=1)).isoformat()},
                        headers=business_auth_headers).status_code == 409
    # NFR-06: only the owning business
    assert client.patch(url, json={"price": "5"}, headers=other_business_auth_headers).status_code == 403
    assert client.patch(url, json={"price": "5"}, headers=customer_auth_headers).status_code == 403
    assert client.patch(url, json={"price": "5"}).status_code == 401
    assert client.patch("/api/v1/slots/nope", json={"price": "5"}, headers=business_auth_headers).status_code == 404


def test_cannot_edit_started_or_removed_slot(
    client: TestClient, db: Session, business_user: User, business_auth_headers
) -> None:
    started = make_slot(db, business_user, hours_ahead=-1)
    assert client.patch(f"/api/v1/slots/{started.id}", json={"price": "5"}, headers=business_auth_headers).status_code == 409
    slot = make_slot(db, business_user)
    assert client.delete(f"/api/v1/slots/{slot.id}", headers=business_auth_headers).status_code == 200
    r = client.patch(f"/api/v1/slots/{slot.id}", json={"price": "5"}, headers=business_auth_headers)
    assert r.status_code == 409 and "removed" in r.json()["detail"].lower()


# ---------------------------------------------------------------- FR-08 remove

def test_remove_available_slot(
    client: TestClient, db: Session, business_user: User, customer_user: User,
    customer_auth_headers, business_auth_headers,
) -> None:
    slot = make_slot(db, business_user)
    r = client.delete(f"/api/v1/slots/{slot.id}", headers=business_auth_headers)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"  # still listed with its status (FR-09)
    listed = client.get("/api/v1/business/slots", headers=business_auth_headers).json()
    assert [s["status"] for s in listed] == ["CANCELLED"]
    # a removed slot can't be booked or waitlisted
    assert _book(client, customer_auth_headers, slot.id).status_code == 409
    assert client.post("/api/v1/waitlist", json={"slot_id": slot.id}, headers=customer_auth_headers).status_code == 409
    assert client.delete(f"/api/v1/slots/{slot.id}", headers=business_auth_headers).status_code == 409  # not twice


def test_remove_booked_slot_is_rejected_and_booking_untouched(
    client: TestClient, db: Session, business_user: User, customer_user: User,
    customer_auth_headers, business_auth_headers,
) -> None:
    slot = make_slot(db, business_user)
    b = _book(client, customer_auth_headers, slot.id).json()
    r = client.delete(f"/api/v1/slots/{slot.id}", headers=business_auth_headers)
    assert r.status_code == 409 and "booked" in r.json()["detail"].lower()
    db.refresh(slot)
    assert slot.status == SlotStatus.BOOKED.value
    assert db.get(Booking, b["id"]).status == BookingStatus.CONFIRMED.value


def test_remove_allowed_again_once_booking_is_cancelled(
    client: TestClient, db: Session, business_user: User, customer_user: User,
    customer_auth_headers, business_auth_headers,
) -> None:
    slot = make_slot(db, business_user)
    b = _book(client, customer_auth_headers, slot.id).json()
    client.post(f"/api/v1/bookings/{b['id']}/cancel", headers=customer_auth_headers)
    assert client.delete(f"/api/v1/slots/{slot.id}", headers=business_auth_headers).status_code == 200
    # the cancellation stays in the history (FR-16)
    hist = client.get("/api/v1/business/bookings", params={"status": "CANCELLED"}, headers=business_auth_headers).json()
    assert len(hist) == 1


def test_remove_authorization(
    client: TestClient, db: Session, business_user: User, other_business_user: User,
    business_auth_headers, other_business_auth_headers, customer_auth_headers,
) -> None:
    slot = make_slot(db, business_user)
    assert client.delete(f"/api/v1/slots/{slot.id}", headers=other_business_auth_headers).status_code == 403
    assert client.delete(f"/api/v1/slots/{slot.id}", headers=customer_auth_headers).status_code == 403
    assert client.delete(f"/api/v1/slots/{slot.id}").status_code == 401
    assert client.delete("/api/v1/slots/nope", headers=business_auth_headers).status_code == 404
    db.refresh(slot)
    assert slot.status == SlotStatus.AVAILABLE.value


# ---------------------------------------------------------------- FR-38 cancellation notices

def test_customer_is_notified_of_their_own_cancellation_and_of_business_cancellation(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_user_2: User,
    customer_auth_headers, customer_2_auth_headers, business_auth_headers,
) -> None:
    s1 = make_slot(db, business_user, hours_ahead=50)
    s2 = make_slot(db, business_user, hours_ahead=60)
    b1 = _book(client, customer_auth_headers, s1.id).json()
    b2 = _book(client, customer_2_auth_headers, s2.id).json()
    client.post(f"/api/v1/bookings/{b1['id']}/cancel", headers=customer_auth_headers)
    client.post(f"/api/v1/bookings/{b2['id']}/cancel", json={"reason": "Closed"}, headers=business_auth_headers)
    own = db.query(Notification).filter(Notification.user_id == customer_user.id, Notification.type == "BOOKING_CANCELLED").all()
    assert len(own) == 1 and "cancelled by you" in own[0].body
    by_business = db.query(Notification).filter(
        Notification.user_id == customer_user_2.id, Notification.type == "BOOKING_CANCELLED_BY_BUSINESS"
    ).all()
    assert len(by_business) == 1
    assert by_business[0].title == "Your appointment was cancelled by the business"
    assert "Reason: Closed" in by_business[0].body and by_business[0].show_in_app
    assert db.query(Notification).filter(
        Notification.user_id == customer_user_2.id, Notification.type == "BOOKING_CANCELLED"
    ).count() == 0
