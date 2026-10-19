from datetime import datetime, timedelta, timezone
from typing import Dict, List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import DeliveryStatus, Notification, NotificationDelivery, PushSubscription, User
from app.services import notification_providers as providers
from app.services.allocation_service import expire_hold
from app.services.notification_service import dispatch_pending
from tests.helpers import make_slot


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> Dict[str, List[tuple]]:
    log: Dict[str, List[tuple]] = {"EMAIL": [], "SMS": [], "PUSH": []}
    monkeypatch.setitem(providers.senders, "EMAIL", lambda *a: log["EMAIL"].append(a))
    monkeypatch.setitem(providers.senders, "SMS", lambda *a: log["SMS"].append(a))
    monkeypatch.setitem(providers.senders, "PUSH", lambda *a: log["PUSH"].append(a))
    return log


def _setup_offer(client: TestClient, db: Session, business_user, customer_user, customer_user_2, h1, h2):
    slot = make_slot(db, business_user, resource="Consult Room")
    b = client.post("/api/v1/bookings", json={"slot_id": slot.id}, headers=h1).json()
    client.post("/api/v1/waitlist", json={"slot_id": slot.id}, headers=h2)
    client.post(f"/api/v1/bookings/{b['id']}/cancel", headers=h1)
    return slot


def test_offer_creates_in_app_notification_and_email_only_by_default(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_user_2: User,
    customer_auth_headers, customer_2_auth_headers, sent,
) -> None:
    _setup_offer(client, db, business_user, customer_user, customer_user_2, customer_auth_headers, customer_2_auth_headers)
    feed = client.get("/api/v1/notifications", headers=customer_2_auth_headers).json()
    assert feed["unread_count"] == 1
    assert feed["items"][0]["type"] == "OFFER_CREATED" and "Consult Room" in feed["items"][0]["body"]

    # no phone and no push subscription -> only an email delivery was queued
    pending = db.query(NotificationDelivery).filter(NotificationDelivery.status == "PENDING").all()
    assert {d.channel for d in pending} == {"EMAIL"}

    assert dispatch_pending(db) == len(pending)
    assert any(args[0] == customer_user_2.email for args in sent["EMAIL"])
    assert dispatch_pending(db) == 0  # nothing is sent twice


def test_sms_and_push_channels_follow_phone_and_subscription(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_user_2: User,
    customer_auth_headers, customer_2_auth_headers, sent,
) -> None:
    r = client.patch("/api/v1/auth/me", json={"phone": "+919876543210"}, headers=customer_2_auth_headers)
    assert r.status_code == 200 and r.json()["phone"] == "+919876543210"
    sub = client.post(
        "/api/v1/notifications/push/subscribe",
        json={"endpoint": "https://push.example/abc123", "keys": {"p256dh": "k", "auth": "a"}},
        headers=customer_2_auth_headers,
    )
    assert sub.status_code == 204
    _setup_offer(client, db, business_user, customer_user, customer_user_2, customer_auth_headers, customer_2_auth_headers)
    dispatch_pending(db)
    assert [a[0] for a in sent["SMS"]] == ["+919876543210"]
    assert len(sent["PUSH"]) == 1 and sent["PUSH"][0][0]["endpoint"] == "https://push.example/abc123"
    assert any(a[0] == customer_user_2.email for a in sent["EMAIL"])


def test_preferences_can_turn_channels_off(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_user_2: User,
    customer_auth_headers, customer_2_auth_headers, sent,
) -> None:
    client.patch("/api/v1/auth/me", json={"phone": "+919876543210", "notify_email": False, "notify_sms": False},
                 headers=customer_2_auth_headers)
    _setup_offer(client, db, business_user, customer_user, customer_user_2, customer_auth_headers, customer_2_auth_headers)
    dispatch_pending(db)
    assert sent["SMS"] == []
    assert all(a[0] != customer_user_2.email for a in sent["EMAIL"])
    # the in-app notification is still there
    assert client.get("/api/v1/notifications", headers=customer_2_auth_headers).json()["unread_count"] == 1


def test_invalid_phone_rejected(client: TestClient, customer_auth_headers) -> None:
    for bad in ("12345", "9876543210", "+0123456789", "call me"):
        assert client.patch("/api/v1/auth/me", json={"phone": bad}, headers=customer_auth_headers).status_code == 422
    assert client.patch("/api/v1/auth/me", json={"phone": ""}, headers=customer_auth_headers).json()["phone"] is None


def test_failed_delivery_retries_with_backoff_then_gives_up(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_user_2: User,
    customer_auth_headers, customer_2_auth_headers, monkeypatch,
) -> None:
    def boom(*a):
        raise ConnectionError("smtp down")
    monkeypatch.setitem(providers.senders, "EMAIL", boom)
    monkeypatch.setattr(settings, "NOTIFICATION_MAX_ATTEMPTS", 3)
    _setup_offer(client, db, business_user, customer_user, customer_user_2, customer_auth_headers, customer_2_auth_headers)
    d = db.query(NotificationDelivery).filter(NotificationDelivery.destination == customer_user_2.email).one()

    t = datetime.now(timezone.utc)
    dispatch_pending(db, now=t)
    db.refresh(d)
    assert d.status == "PENDING" and d.attempts == 1 and "smtp down" in d.last_error
    assert d.next_attempt_at.replace(tzinfo=timezone.utc) > t

    assert dispatch_pending(db, now=t) == 0  # not due yet -> not retried immediately
    db.refresh(d)
    assert d.attempts == 1

    for _ in range(2):
        t += timedelta(hours=1)
        dispatch_pending(db, now=t)
    db.refresh(d)
    assert d.status == DeliveryStatus.FAILED.value and d.attempts == 3


def test_dead_push_subscription_is_removed_and_not_retried(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_user_2: User,
    customer_auth_headers, customer_2_auth_headers, monkeypatch, sent,
) -> None:
    def gone(*a):
        raise providers.PermanentDeliveryError("push subscription is gone")
    client.post("/api/v1/notifications/push/subscribe",
                json={"endpoint": "https://push.example/dead00", "keys": {"p256dh": "k", "auth": "a"}},
                headers=customer_2_auth_headers)
    monkeypatch.setitem(providers.senders, "PUSH", gone)
    _setup_offer(client, db, business_user, customer_user, customer_user_2, customer_auth_headers, customer_2_auth_headers)
    dispatch_pending(db)
    assert db.query(PushSubscription).count() == 0
    d = db.query(NotificationDelivery).filter(NotificationDelivery.channel == "PUSH").one()
    assert d.status == "FAILED" and d.attempts == 0


def test_rolled_back_transaction_sends_nothing(db: Session, business_user: User, customer_user: User, sent) -> None:
    from app.services.notification_service import enqueue
    enqueue(db, customer_user.id, "X", "t", "b")
    db.rollback()
    assert db.query(Notification).count() == 0
    assert dispatch_pending(db) == 0 and sent["EMAIL"] == []


def test_expired_offer_notifies_expired_user_and_next_in_line(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_user_2: User,
    other_customer_user: User, customer_auth_headers, customer_2_auth_headers, other_customer_auth_headers,
) -> None:
    from app.models import Hold
    slot = make_slot(db, business_user)
    b = client.post("/api/v1/bookings", json={"slot_id": slot.id}, headers=customer_auth_headers).json()
    client.post("/api/v1/waitlist", json={"slot_id": slot.id}, headers=customer_2_auth_headers)
    client.post("/api/v1/waitlist", json={"slot_id": slot.id}, headers=other_customer_auth_headers)
    client.post(f"/api/v1/bookings/{b['id']}/cancel", headers=customer_auth_headers)
    hold = db.query(Hold).filter(Hold.user_id == customer_user_2.id).one()
    expire_hold(db, hold.id)
    types2 = [n.type for n in db.query(Notification).filter(Notification.user_id == customer_user_2.id)]
    assert "OFFER_EXPIRED" in types2
    assert db.query(Notification).filter(
        Notification.user_id == other_customer_user.id, Notification.type == "OFFER_CREATED").count() == 1


def test_mark_read_and_isolation_between_users(
    client: TestClient, db: Session, business_user: User, customer_user: User, customer_user_2: User,
    customer_auth_headers, customer_2_auth_headers,
) -> None:
    _setup_offer(client, db, business_user, customer_user, customer_user_2, customer_auth_headers, customer_2_auth_headers)
    nid = client.get("/api/v1/notifications", headers=customer_2_auth_headers).json()["items"][0]["id"]
    assert client.post(f"/api/v1/notifications/{nid}/read", headers=customer_auth_headers).status_code == 404
    assert client.post(f"/api/v1/notifications/{nid}/read", headers=customer_2_auth_headers).status_code == 200
    assert client.get("/api/v1/notifications", headers=customer_2_auth_headers).json()["unread_count"] == 0
    assert client.get("/api/v1/notifications").status_code == 401
    assert client.post("/api/v1/notifications/read-all", headers=customer_2_auth_headers).status_code == 204


def test_provider_console_fallback_does_not_raise() -> None:
    providers.send_email("a@b.c", "s", "b")
    providers.send_sms("+919876543210", "b")
    providers.send_push({"endpoint": "x"}, "t", "b", None)
