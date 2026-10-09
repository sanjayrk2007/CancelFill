from typing import Dict
from fastapi.testclient import TestClient
from app.models import User


def test_update_name_success(
    client: TestClient,
    customer_user: User,
    customer_auth_headers: Dict[str, str],
) -> None:
    res = client.patch(
        "/api/v1/auth/me",
        json={"name": "Updated Name"},
        headers=customer_auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Updated Name"
    assert data["email"] == customer_user.email


def test_update_name_too_long(
    client: TestClient,
    customer_auth_headers: Dict[str, str],
) -> None:
    res = client.patch(
        "/api/v1/auth/me",
        json={"name": "A" * 61},
        headers=customer_auth_headers,
    )
    assert res.status_code == 422


def test_update_name_empty(
    client: TestClient,
    customer_auth_headers: Dict[str, str],
) -> None:
    res = client.patch(
        "/api/v1/auth/me",
        json={"name": ""},
        headers=customer_auth_headers,
    )
    assert res.status_code == 422


def test_update_name_unauthenticated(client: TestClient) -> None:
    res = client.patch("/api/v1/auth/me", json={"name": "Someone"})
    assert res.status_code == 401


def test_change_password_success(
    client: TestClient,
    customer_user: User,
    customer_auth_headers: Dict[str, str],
) -> None:
    res = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "password123", "new_password": "newpassword99"},
        headers=customer_auth_headers,
    )
    assert res.status_code == 204

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": customer_user.email, "password": "newpassword99"},
    )
    assert login_res.status_code == 200


def test_change_password_wrong_current(
    client: TestClient,
    customer_auth_headers: Dict[str, str],
) -> None:
    res = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrongpassword", "new_password": "newpassword99"},
        headers=customer_auth_headers,
    )
    assert res.status_code == 400
    assert "incorrect" in res.json()["detail"].lower()


def test_change_password_too_short(
    client: TestClient,
    customer_auth_headers: Dict[str, str],
) -> None:
    res = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "password123", "new_password": "short"},
        headers=customer_auth_headers,
    )
    assert res.status_code == 422


def test_change_password_unauthenticated(client: TestClient) -> None:
    res = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "password123", "new_password": "newpassword99"},
    )
    assert res.status_code == 401


def test_customer_stats_empty(
    client: TestClient,
    customer_auth_headers: Dict[str, str],
) -> None:
    res = client.get("/api/v1/me/stats", headers=customer_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_bookings"] == 0
    assert data["upcoming_bookings"] == 0
    assert data["recovered_bookings"] == 0
    assert data["offers_received"] == 0
    assert data["offers_accepted"] == 0
    assert data["offers_declined"] == 0
    assert data["offers_expired"] == 0
    assert data["acceptance_rate"] == 0.0
    assert data["active_waitlist_entries"] == 0
    assert data["cancelled_bookings"] == 0


def test_customer_stats_forbidden_for_business(
    client: TestClient,
    business_auth_headers: Dict[str, str],
) -> None:
    res = client.get("/api/v1/me/stats", headers=business_auth_headers)
    assert res.status_code == 403


def test_customer_stats_unauthenticated(client: TestClient) -> None:
    res = client.get("/api/v1/me/stats")
    assert res.status_code == 401
