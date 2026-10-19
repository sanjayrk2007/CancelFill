import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Dict

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Booking, Hold, HoldStatus, Notification, Payment, PaymentStatus, Slot, SlotStatus, User
from app.services import payment_gateways
from app.services.allocation_service import expire_hold
from app.services.payment_service import process_pending_refunds
from tests.helpers import make_slot
from tests.invariants import assert_invariants


@pytest.fixture(autouse=True)
def mock_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "mock")


def _checkout(client, headers, **body):
    return client.post("/api/v1/payments/checkout", json=body, headers=headers)


def _pay(client, headers, checkout: dict):
    creds = client.post(f"/api/v1/payments/{checkout['payment_id']}/mock-pay", headers=headers).json()
    return client.post("/api/v1/payments/confirm", json={"payment_id": checkout["payment_id"], **creds}, headers=headers)


def _webhook(client, event: dict, secret: str = None, sig: str = None):
    raw = json.dumps(event).encode()
    sig = sig or hmac.new((secret or settings.MOCK_PAYMENT_SECRET).encode(), raw, hashlib.sha256).hexdigest()
    return client.post("/api/v1/payments/webhook", content=raw, headers={"X-Razorpay-Signature": sig})


# ------------------------------------------------------------ config & gating

def test_config_reports_provider(client: TestClient, monkeypatch) -> None:
    assert client.get("/api/v1/payments/config").json() == {
        "enabled": True, "provider": "mock", "key_id": "mock_key", "currency": "INR"}
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "none")
    assert client.get("/api/v1/payments/config").json()["enabled"] is False


def test_paid_slot_cannot_be_booked_directly_but_free_slot_can(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_auth_headers
) -> None:
    paid = make_slot(db, business_user, price="500")
    free = make_slot(db, business_user, price="0", hours_ahead=60)
    r = client.post("/api/v1/bookings", json={"slot_id": paid.id}, headers=customer_auth_headers)
    assert r.status_code == 402
    assert client.post("/api/v1/bookings", json={"slot_id": free.id}, headers=customer_auth_headers).status_code == 201
    assert _checkout(client, customer_auth_headers, slot_id=free.id).status_code == 409  # nothing to pay


def test_payments_disabled_keeps_old_behaviour(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_auth_headers, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "none")
    slot = make_slot(db, business_user, price="500")
    assert client.post("/api/v1/bookings", json={"slot_id": slot.id}, headers=customer_auth_headers).status_code == 201
    assert _checkout(client, customer_auth_headers, slot_id=slot.id).status_code == 409


# ------------------------------------------------------------ happy path

def test_direct_booking_checkout_pay_confirm(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_auth_headers
) -> None:
    slot = make_slot(db, business_user, price="750.50")
    co = _checkout(client, customer_auth_headers, slot_id=slot.id)
    assert co.status_code == 200
    data = co.json()
    assert data["amount_minor"] == 75050 and data["currency"] == "INR" and data["provider"] == "mock"

    db.refresh(slot)
    assert slot.status == SlotStatus.HELD.value  # seat is reserved while paying
    assert_invariants(db)

    r = _pay(client, customer_auth_headers, data)
    assert r.status_code == 200 and r.json()["source"] == "DIRECT" and r.json()["recovered_from_booking_id"] is None
    db.refresh(slot)
    assert slot.status == SlotStatus.BOOKED.value
    pay = db.get(Payment, data["payment_id"])
    db.refresh(pay)
    assert pay.status == PaymentStatus.PAID.value and pay.booking_id == r.json()["id"]
    assert_invariants(db)

    mine = client.get("/api/v1/payments", headers=customer_auth_headers).json()
    assert [p["status"] for p in mine] == ["PAID"]
    bookings = client.get("/api/v1/me/bookings", headers=customer_auth_headers).json()
    assert bookings[0]["payment_status"] == "PAID"


def test_checkout_hold_is_not_listed_as_a_waitlist_offer(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_auth_headers
) -> None:
    slot = make_slot(db, business_user, price="100")
    _checkout(client, customer_auth_headers, slot_id=slot.id)
    assert client.get("/api/v1/me/offers", headers=customer_auth_headers).json() == []
    assert client.get("/api/v1/me/stats", headers=customer_auth_headers).json()["offers_received"] == 0


def test_checkout_retry_reuses_same_order(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_auth_headers
) -> None:
    slot = make_slot(db, business_user, price="100")
    a = _checkout(client, customer_auth_headers, slot_id=slot.id).json()
    b = _checkout(client, customer_auth_headers, slot_id=slot.id).json()
    assert a["payment_id"] == b["payment_id"] and a["hold_id"] == b["hold_id"]
    assert db.query(Hold).count() == 1 and db.query(Payment).count() == 1


def test_waitlist_offer_must_be_paid_for(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_user_2: User,
    customer_auth_headers, customer_2_auth_headers,
) -> None:
    slot = make_slot(db, business_user, price="300")
    first = _checkout(client, customer_auth_headers, slot_id=slot.id).json()
    _pay(client, customer_auth_headers, first)
    booking_id = db.query(Booking).one().id
    client.post("/api/v1/waitlist", json={"slot_id": slot.id}, headers=customer_2_auth_headers)
    client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=customer_auth_headers)

    offer = client.get("/api/v1/me/offers", headers=customer_2_auth_headers).json()[0]
    assert client.post(f"/api/v1/holds/{offer['id']}/accept", headers=customer_2_auth_headers).status_code == 402
    co = _checkout(client, customer_2_auth_headers, hold_id=offer["id"]).json()
    r = _pay(client, customer_2_auth_headers, co)
    assert r.status_code == 200 and r.json()["source"] == "RECOVERED"
    assert_invariants(db)


# ------------------------------------------------------------ security

def test_tampered_or_foreign_signature_rejected(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_user_2: User,
    customer_auth_headers, customer_2_auth_headers,
) -> None:
    slot = make_slot(db, business_user, price="100")
    co = _checkout(client, customer_auth_headers, slot_id=slot.id).json()
    creds = client.post(f"/api/v1/payments/{co['payment_id']}/mock-pay", headers=customer_auth_headers).json()
    body = {"payment_id": co["payment_id"], **creds}

    assert client.post("/api/v1/payments/confirm", json={**body, "signature": "0" * 64},
                       headers=customer_auth_headers).status_code == 400
    assert client.post("/api/v1/payments/confirm", json={**body, "provider_payment_id": "pay_other"},
                       headers=customer_auth_headers).status_code == 400
    assert client.post("/api/v1/payments/confirm", json={**body, "provider_order_id": "order_other"},
                       headers=customer_auth_headers).status_code == 400
    # another customer cannot confirm (or even simulate paying) someone else's order
    assert client.post("/api/v1/payments/confirm", json=body, headers=customer_2_auth_headers).status_code == 403
    assert client.post(f"/api/v1/payments/{co['payment_id']}/mock-pay", headers=customer_2_auth_headers).status_code == 403
    assert db.query(Booking).count() == 0
    # the genuine credentials still work afterwards
    assert client.post("/api/v1/payments/confirm", json=body, headers=customer_auth_headers).status_code == 200


def test_confirm_is_idempotent(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_auth_headers
) -> None:
    slot = make_slot(db, business_user, price="100")
    co = _checkout(client, customer_auth_headers, slot_id=slot.id).json()
    creds = client.post(f"/api/v1/payments/{co['payment_id']}/mock-pay", headers=customer_auth_headers).json()
    body = {"payment_id": co["payment_id"], **creds}
    r1 = client.post("/api/v1/payments/confirm", json=body, headers=customer_auth_headers)
    r2 = client.post("/api/v1/payments/confirm", json=body, headers=customer_auth_headers)
    assert r1.status_code == r2.status_code == 200 and r1.json()["id"] == r2.json()["id"]
    assert db.query(Booking).count() == 1


def test_cannot_pay_for_someone_elses_hold(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_user_2: User,
    customer_auth_headers, customer_2_auth_headers,
) -> None:
    slot = make_slot(db, business_user, price="100")
    co = _checkout(client, customer_auth_headers, slot_id=slot.id).json()
    assert _checkout(client, customer_2_auth_headers, hold_id=co["hold_id"]).status_code == 403
    assert _checkout(client, customer_2_auth_headers, slot_id=slot.id).status_code == 409  # seat is taken
    assert _checkout(client, customer_2_auth_headers).status_code in (409, 422)


def test_mock_pay_endpoint_unavailable_for_real_provider(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_auth_headers, monkeypatch
) -> None:
    slot = make_slot(db, business_user, price="100")
    co = _checkout(client, customer_auth_headers, slot_id=slot.id).json()
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "razorpay")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_x")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "secret")
    assert client.post(f"/api/v1/payments/{co['payment_id']}/mock-pay", headers=customer_auth_headers).status_code == 404


# ------------------------------------------------------------ hold lifecycle

def test_abandoned_checkout_releases_seat_and_expires_order(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_user_2: User,
    customer_auth_headers, customer_2_auth_headers,
) -> None:
    slot = make_slot(db, business_user, price="100")
    co = _checkout(client, customer_auth_headers, slot_id=slot.id).json()
    expire_hold(db, co["hold_id"])
    db.refresh(slot)
    assert slot.status == SlotStatus.AVAILABLE.value
    assert db.get(Payment, co["payment_id"]).status == PaymentStatus.EXPIRED.value
    assert _checkout(client, customer_2_auth_headers, slot_id=slot.id).status_code == 200  # seat is free again


def test_paying_after_hold_expired_is_refunded_not_booked(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_auth_headers
) -> None:
    slot = make_slot(db, business_user, price="100")
    co = _checkout(client, customer_auth_headers, slot_id=slot.id).json()
    creds = client.post(f"/api/v1/payments/{co['payment_id']}/mock-pay", headers=customer_auth_headers).json()
    hold = db.get(Hold, co["hold_id"])
    hold.expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    db.commit()
    r = client.post("/api/v1/payments/confirm", json={"payment_id": co["payment_id"], **creds}, headers=customer_auth_headers)
    assert r.status_code == 409 and "refund" in r.json()["detail"].lower()
    assert db.query(Booking).count() == 0
    pay = db.get(Payment, co["payment_id"])
    db.refresh(pay)
    assert pay.status == PaymentStatus.REFUND_PENDING.value
    assert process_pending_refunds(db) == 1
    db.refresh(pay)
    assert pay.status == PaymentStatus.REFUNDED.value and pay.refund_id.startswith("rfnd_mock_")
    assert_invariants(db)


def test_decline_checkout_hold_via_api_releases_it(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_auth_headers
) -> None:
    slot = make_slot(db, business_user, price="100")
    co = _checkout(client, customer_auth_headers, slot_id=slot.id).json()
    assert client.post(f"/api/v1/holds/{co['hold_id']}/decline", headers=customer_auth_headers).status_code == 200
    db.refresh(slot)
    assert slot.status == SlotStatus.AVAILABLE.value


# ------------------------------------------------------------ webhooks

def _captured_event(order_id: str, payment_id: str) -> dict:
    return {"event": "payment.captured", "payload": {"payment": {"entity": {"id": payment_id, "order_id": order_id}}}}


def test_webhook_confirms_booking_when_browser_never_returns(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_auth_headers
) -> None:
    slot = make_slot(db, business_user, price="100")
    co = _checkout(client, customer_auth_headers, slot_id=slot.id).json()
    r = _webhook(client, _captured_event(co["provider_order_id"], "pay_abc123"))
    assert r.status_code == 200
    booking = db.query(Booking).one()
    assert booking.status == "CONFIRMED"
    pay = db.get(Payment, co["payment_id"])
    db.refresh(pay)
    assert pay.status == PaymentStatus.PAID.value and pay.booking_id == booking.id
    # redelivery of the same webhook changes nothing
    assert _webhook(client, _captured_event(co["provider_order_id"], "pay_abc123")).status_code == 200
    assert db.query(Booking).count() == 1


def test_webhook_for_expired_order_refunds_automatically(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_auth_headers
) -> None:
    slot = make_slot(db, business_user, price="100")
    co = _checkout(client, customer_auth_headers, slot_id=slot.id).json()
    expire_hold(db, co["hold_id"])
    assert _webhook(client, _captured_event(co["provider_order_id"], "pay_late1")).status_code == 200
    pay = db.get(Payment, co["payment_id"])
    db.refresh(pay)
    assert pay.status == PaymentStatus.REFUND_PENDING.value and db.query(Booking).count() == 0


def test_webhook_rejects_bad_or_missing_signature(client: TestClient) -> None:
    ev = _captured_event("order_x", "pay_x")
    assert _webhook(client, ev, sig="deadbeef").status_code == 400
    assert _webhook(client, ev, secret="wrong-secret").status_code == 400
    assert client.post("/api/v1/payments/webhook", content=json.dumps(ev)).status_code == 400


def test_webhook_unknown_order_and_event_are_ignored(client: TestClient) -> None:
    assert _webhook(client, _captured_event("order_unknown", "pay_1")).status_code == 200
    assert _webhook(client, {"event": "something.else", "payload": {}}).status_code == 200


# ------------------------------------------------------------ refunds

def _book_and_pay(client, db, owner, headers, price="400", hours_ahead=72):
    slot = make_slot(db, owner, price=price, hours_ahead=hours_ahead)
    co = _checkout(client, headers, slot_id=slot.id).json()
    booking = _pay(client, headers, co).json()
    return slot, co, booking


def test_business_cancellation_always_refunds(
    client: TestClient, db: Session, business_user: User, customer_user: User,
    customer_auth_headers, business_auth_headers,
) -> None:
    slot, co, booking = _book_and_pay(client, db, business_user, customer_auth_headers, hours_ahead=1)  # inside cutoff
    r = client.post(f"/api/v1/bookings/{booking['id']}/cancel", json={"reason": "Closed"}, headers=business_auth_headers)
    assert r.status_code == 200
    assert db.get(Payment, co["payment_id"]).status == PaymentStatus.REFUND_PENDING.value
    assert process_pending_refunds(db) == 1
    pay = db.get(Payment, co["payment_id"])
    db.refresh(pay)
    assert pay.status == PaymentStatus.REFUNDED.value and pay.refunded_at is not None
    assert db.query(Notification).filter(Notification.type == "REFUND_ISSUED", Notification.user_id == customer_user.id).count() == 1
    assert process_pending_refunds(db) == 0  # no double refund


def test_customer_cancellation_refund_follows_cutoff(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_user_2: User,
    customer_auth_headers, customer_2_auth_headers,
) -> None:
    far_slot, far_co, far_b = _book_and_pay(client, db, business_user, customer_auth_headers, hours_ahead=settings.REFUND_CUTOFF_HOURS + 24)
    near_slot, near_co, near_b = _book_and_pay(client, db, business_user, customer_2_auth_headers, hours_ahead=settings.REFUND_CUTOFF_HOURS - 20)
    client.post(f"/api/v1/bookings/{far_b['id']}/cancel", headers=customer_auth_headers)
    client.post(f"/api/v1/bookings/{near_b['id']}/cancel", headers=customer_2_auth_headers)
    assert db.get(Payment, far_co["payment_id"]).status == PaymentStatus.REFUND_PENDING.value
    assert db.get(Payment, near_co["payment_id"]).status == PaymentStatus.PAID.value  # kept: late cancellation


def test_removing_a_paid_booked_slot_is_rejected_and_nothing_is_refunded(
    client: TestClient, db: Session, business_user: User, customer_user: User,
    customer_auth_headers, business_auth_headers,
) -> None:
    """FR-08: a booked slot can't be removed. The business must cancel the booking first, which refunds it."""
    slot, co, booking = _book_and_pay(client, db, business_user, customer_auth_headers)
    assert client.delete(f"/api/v1/slots/{slot.id}", headers=business_auth_headers).status_code == 409
    assert db.get(Payment, co["payment_id"]).status == PaymentStatus.PAID.value
    # the sanctioned route: cancel the booking (refunded in full), then the slot is free to remove
    client.post(f"/api/v1/bookings/{booking['id']}/cancel", json={"reason": "Closing"}, headers=business_auth_headers)
    assert process_pending_refunds(db) == 1
    assert client.delete(f"/api/v1/slots/{slot.id}", headers=business_auth_headers).status_code == 200


def test_refund_failure_retries_then_marks_failed(
    client: TestClient, db: Session, business_user: User, customer_user: User,
    customer_auth_headers, business_auth_headers, monkeypatch,
) -> None:
    slot, co, booking = _book_and_pay(client, db, business_user, customer_auth_headers)
    client.post(f"/api/v1/bookings/{booking['id']}/cancel", json={"reason": "x"}, headers=business_auth_headers)

    def fail(self, *a):
        raise payment_gateways.GatewayError("gateway down")
    monkeypatch.setattr(payment_gateways.MockGateway, "refund", fail)
    for _ in range(5):
        assert process_pending_refunds(db) == 0
    pay = db.get(Payment, co["payment_id"])
    db.refresh(pay)
    assert pay.status == PaymentStatus.REFUND_FAILED.value and pay.refund_attempts == 5


def test_refund_webhook_marks_refunded_idempotently(
    client: TestClient, db: Session, business_user: User, customer_user: User,
    customer_auth_headers, business_auth_headers,
) -> None:
    slot, co, booking = _book_and_pay(client, db, business_user, customer_auth_headers)
    client.post(f"/api/v1/bookings/{booking['id']}/cancel", json={"reason": "x"}, headers=business_auth_headers)
    pay = db.get(Payment, co["payment_id"])
    db.refresh(pay)
    ev = {"event": "refund.processed", "payload": {"refund": {"entity": {"id": "rfnd_1", "payment_id": pay.provider_payment_id}}}}
    assert _webhook(client, ev).status_code == 200 and _webhook(client, ev).status_code == 200
    db.refresh(pay)
    assert pay.status == PaymentStatus.REFUNDED.value and pay.refund_id == "rfnd_1"


def test_business_payments_listing_scoped_to_owner(
    client: TestClient, db: Session, business_user: User, other_business_user: User, customer_user: User,
    customer_auth_headers, business_auth_headers, other_business_auth_headers,
) -> None:
    _book_and_pay(client, db, business_user, customer_auth_headers)
    rows = client.get("/api/v1/business/payments", headers=business_auth_headers).json()
    assert len(rows) == 1 and rows[0]["customer_name"] == "Customer One" and rows[0]["status"] == "PAID"
    assert client.get("/api/v1/business/payments", headers=other_business_auth_headers).json() == []
    assert client.get("/api/v1/business/payments", headers=customer_auth_headers).status_code == 403


# ------------------------------------------------------------ razorpay adapter (HTTP mocked)

def test_razorpay_adapter_requests_and_signature(monkeypatch) -> None:
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "razorpay")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_abc")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "topsecret")
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "whsecret")
    calls = []

    def fake_post(url, json=None, auth=None, timeout=None):
        calls.append((url, json, auth))
        return httpx.Response(200, json={"id": "order_RZP1" if url.endswith("/orders") else "rfnd_RZP1"})
    monkeypatch.setattr(httpx, "post", fake_post)

    gw = payment_gateways.get_gateway()
    assert gw.name == "razorpay" and gw.key_id == "rzp_test_abc"
    assert gw.create_order(50000, "INR", "hold_1") == "order_RZP1"
    assert calls[0][0] == "https://api.razorpay.com/v1/orders"
    assert calls[0][1]["amount"] == 50000 and calls[0][1]["currency"] == "INR" and calls[0][2] == ("rzp_test_abc", "topsecret")
    assert gw.refund("pay_1", 50000, "because") == "rfnd_RZP1"
    assert calls[1][0].endswith("/payments/pay_1/refund") and calls[1][1]["amount"] == 50000

    good = hmac.new(b"topsecret", b"order_1|pay_1", hashlib.sha256).hexdigest()
    assert gw.verify_payment_signature("order_1", "pay_1", good)
    assert not gw.verify_payment_signature("order_1", "pay_2", good)
    body = b'{"x":1}'
    assert gw.verify_webhook(body, hmac.new(b"whsecret", body, hashlib.sha256).hexdigest())
    assert not gw.verify_webhook(body, hmac.new(b"topsecret", body, hashlib.sha256).hexdigest())


def test_razorpay_api_error_surfaces_as_gateway_error(monkeypatch) -> None:
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "razorpay")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "k")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "s")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(400, text="bad request"))
    with pytest.raises(payment_gateways.GatewayError):
        payment_gateways.get_gateway().create_order(100, "INR", "r")


def test_razorpay_without_keys_is_a_clear_error(monkeypatch) -> None:
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "razorpay")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "")
    with pytest.raises(payment_gateways.GatewayError):
        payment_gateways.get_gateway()


def test_failed_payment_on_an_offer_cascades_like_a_decline(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_user_2: User,
    other_customer_user: User, customer_auth_headers, customer_2_auth_headers, other_customer_auth_headers,
) -> None:
    """SRS 3.12: a failed payment is treated the same way as a declined offer."""
    slot, _, booking = _book_and_pay(client, db, business_user, customer_auth_headers)
    client.post("/api/v1/waitlist", json={"slot_id": slot.id}, headers=customer_2_auth_headers)
    client.post("/api/v1/waitlist", json={"slot_id": slot.id}, headers=other_customer_auth_headers)
    client.post(f"/api/v1/bookings/{booking['id']}/cancel", headers=customer_auth_headers)

    offer = client.get("/api/v1/me/offers", headers=customer_2_auth_headers).json()[0]
    co = _checkout(client, customer_2_auth_headers, hold_id=offer["id"]).json()
    # the customer never completes payment; the client reports it as a decline
    assert client.post(f"/api/v1/holds/{offer['id']}/decline", headers=customer_2_auth_headers).status_code == 200

    assert db.get(Payment, co["payment_id"]).status == PaymentStatus.EXPIRED.value
    assert db.query(Booking).filter(Booking.user_id == customer_user_2.id, Booking.status == "CONFIRMED").count() == 0
    nxt = client.get("/api/v1/me/offers", headers=other_customer_auth_headers).json()
    assert len(nxt) == 1 and nxt[0]["slot_id"] == slot.id  # offered to the next candidate
    assert_invariants(db)
