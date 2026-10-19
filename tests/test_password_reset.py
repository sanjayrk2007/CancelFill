import re
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Notification, NotificationDelivery, PasswordResetToken, User


def _request_token(client: TestClient, db: Session, email: str) -> str:
    r = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert r.status_code == 200
    n = db.query(Notification).filter(Notification.type == "PASSWORD_RESET").order_by(Notification.created_at.desc()).first()
    return re.search(r"token=([\w-]+)", n.body).group(1)


def _login(client: TestClient, email: str, password: str):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_full_reset_flow(client: TestClient, db: Session, customer_user: User) -> None:
    token = _request_token(client, db, customer_user.email)
    r = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "brand-new-pass"})
    assert r.status_code == 200
    assert _login(client, customer_user.email, "password123").status_code == 401
    assert _login(client, customer_user.email, "brand-new-pass").status_code == 200


def test_token_is_single_use(client: TestClient, db: Session, customer_user: User) -> None:
    token = _request_token(client, db, customer_user.email)
    assert client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "first-new-pass"}).status_code == 200
    again = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "second-new-pass"})
    assert again.status_code == 400
    assert _login(client, customer_user.email, "first-new-pass").status_code == 200


def test_expired_and_garbage_tokens_rejected(client: TestClient, db: Session, customer_user: User) -> None:
    token = _request_token(client, db, customer_user.email)
    rec = db.query(PasswordResetToken).one()
    rec.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "whatever-123"}).status_code == 400
    assert client.post("/api/v1/auth/reset-password", json={"token": "x" * 40, "new_password": "whatever-123"}).status_code == 400
    assert _login(client, customer_user.email, "password123").status_code == 200


def test_new_request_invalidates_older_link(client: TestClient, db: Session, customer_user: User) -> None:
    old = _request_token(client, db, customer_user.email)
    new = _request_token(client, db, customer_user.email)
    assert old != new
    assert client.post("/api/v1/auth/reset-password", json={"token": old, "new_password": "whatever-123"}).status_code == 400
    assert client.post("/api/v1/auth/reset-password", json={"token": new, "new_password": "whatever-123"}).status_code == 200


def test_unknown_email_gets_identical_response_and_sends_nothing(client: TestClient, db: Session, customer_user: User) -> None:
    known = client.post("/api/v1/auth/forgot-password", json={"email": customer_user.email})
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert db.query(Notification).count() == 1  # only the real user got one


def test_reset_email_is_email_only_hidden_and_ignores_preferences(
    client: TestClient, db: Session, customer_user: User, customer_auth_headers
) -> None:
    customer_user.notify_email = False
    customer_user.phone = "+919876543210"
    db.commit()
    _request_token(client, db, customer_user.email)
    deliveries = db.query(NotificationDelivery).all()
    assert [d.channel for d in deliveries] == ["EMAIL"]  # never SMS, even with a phone on file
    # the link must not leak through the in-app notification feed
    feed = client.get("/api/v1/notifications", headers=customer_auth_headers).json()
    assert feed["items"] == []


def test_token_stored_hashed_and_short_password_rejected(client: TestClient, db: Session, customer_user: User) -> None:
    token = _request_token(client, db, customer_user.email)
    assert db.query(PasswordResetToken).one().token_hash != token
    assert client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "short"}).status_code == 422
