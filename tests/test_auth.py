from typing import Dict
import pytest
from fastapi.testclient import TestClient
from app.models import User

def test_register_customer_and_business(client: TestClient) -> None:
    res_cust = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newcust@example.com",
            "password": "securepass123",
            "name": "New Customer",
            "role": "CUSTOMER",
            "phone": "+919876543210"
        }
    )
    assert res_cust.status_code == 201
    cust_data = res_cust.json()
    assert cust_data["email"] == "newcust@example.com"
    assert cust_data["role"] == "CUSTOMER"
    assert cust_data["phone"] == "+919876543210"
    assert "id" in cust_data

    res_biz = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newbiz@example.com",
            "password": "securepass123",
            "name": "New Business",
            "role": "BUSINESS",
            "business_name": "New Business LLC",
            "category": "SALON",
            "contact_phone": "+919876543211",
            "contact_address": "123 Main St"
        }
    )
    assert res_biz.status_code == 201
    biz_data = res_biz.json()
    assert biz_data["email"] == "newbiz@example.com"
    assert biz_data["role"] == "BUSINESS"
    assert biz_data["business_name"] == "New Business LLC"
    assert biz_data["category"] == "SALON"
    assert biz_data["contact_phone"] == "+919876543211"
    assert biz_data["contact_address"] == "123 Main St"

def test_register_duplicate_email(client: TestClient) -> None:
    payload = {
        "email": "dup@example.com",
        "password": "pass",
        "name": "User 1",
        "role": "CUSTOMER",
        "phone": "+919876543210"
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert res2.json()["detail"] == "Email already registered"

def test_login_success_and_failure(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "logintest@example.com",
            "password": "mypassword",
            "name": "Login User",
            "role": "CUSTOMER",
            "phone": "+919876543210"
        }
    )

    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": "logintest@example.com", "password": "mypassword"}
    )
    assert res_login.status_code == 200
    token_data = res_login.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    res_wrong_pw = client.post(
        "/api/v1/auth/login",
        json={"email": "logintest@example.com", "password": "wrongpassword"}
    )
    assert res_wrong_pw.status_code == 401

    res_unknown_email = client.post(
        "/api/v1/auth/login",
        json={"email": "nosuch@example.com", "password": "mypassword"}
    )
    assert res_unknown_email.status_code == 401

def test_login_form_urlencoded(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "formuser@example.com",
            "password": "mypassword",
            "name": "Form User",
            "role": "BUSINESS",
            "business_name": "Form Business",
            "category": "OTHER",
            "contact_phone": "+919876543210"
        }
    )

    res = client.post(
        "/api/v1/auth/login",
        data={"username": "formuser@example.com", "password": "mypassword"}
    )
    assert res.status_code == 200
    assert "access_token" in res.json()

def test_get_me(
    client: TestClient,
    customer_user: User,
    customer_auth_headers: Dict[str, str]
) -> None:
    res_unauth = client.get("/api/v1/auth/me")
    assert res_unauth.status_code == 401

    res = client.get("/api/v1/auth/me", headers=customer_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == customer_user.id
    assert data["email"] == customer_user.email
    assert data["role"] == "CUSTOMER"

def test_startup_default_jwt_secret_warning(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    from unittest.mock import patch
    from fastapi import FastAPI
    from app.main import lifespan
    from app.config import settings, DEFAULT_JWT_SECRET
    import anyio

    async def _run() -> None:
        test_app = FastAPI()
        with patch.object(settings, "JWT_SECRET", DEFAULT_JWT_SECRET):
            with patch.object(settings, "DATABASE_URL", "postgresql://user:pass@localhost/db"):
                with caplog.at_level(logging.WARNING):
                    async with lifespan(test_app):
                        pass

    anyio.run(_run)
    assert any("SECURITY WARNING" in record.message for record in caplog.records)

def test_register_customer_missing_phone(client: TestClient) -> None:
    res_missing = client.post(
        "/api/v1/auth/register",
        json={
            "email": "nophone@example.com",
            "password": "password123",
            "name": "No Phone",
            "role": "CUSTOMER"
        }
    )
    assert res_missing.status_code == 422

    res_invalid = client.post(
        "/api/v1/auth/register",
        json={
            "email": "badphone@example.com",
            "password": "password123",
            "name": "Bad Phone",
            "role": "CUSTOMER",
            "phone": "123"
        }
    )
    assert res_invalid.status_code == 422

def test_register_business_missing_fields(client: TestClient) -> None:
    res_no_biz_name = client.post(
        "/api/v1/auth/register",
        json={
            "email": "nobizname@example.com",
            "password": "password123",
            "name": "Owner",
            "role": "BUSINESS",
            "category": "SALON",
            "contact_phone": "+919876543210"
        }
    )
    assert res_no_biz_name.status_code == 422

    res_no_category = client.post(
        "/api/v1/auth/register",
        json={
            "email": "nocat@example.com",
            "password": "password123",
            "name": "Owner",
            "role": "BUSINESS",
            "business_name": "My Biz",
            "contact_phone": "+919876543210"
        }
    )
    assert res_no_category.status_code == 422

    res_bad_category = client.post(
        "/api/v1/auth/register",
        json={
            "email": "badcat@example.com",
            "password": "password123",
            "name": "Owner",
            "role": "BUSINESS",
            "business_name": "My Biz",
            "category": "INVALID_CAT",
            "contact_phone": "+919876543210"
        }
    )
    assert res_bad_category.status_code == 422

    res_no_contact_phone = client.post(
        "/api/v1/auth/register",
        json={
            "email": "nophonebiz@example.com",
            "password": "password123",
            "name": "Owner",
            "role": "BUSINESS",
            "business_name": "My Biz",
            "category": "SALON"
        }
    )
    assert res_no_contact_phone.status_code == 422

def test_business_profile_edit_and_get_me(client: TestClient) -> None:
    res_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "editbiz@example.com",
            "password": "password123",
            "name": "Biz Owner",
            "role": "BUSINESS",
            "business_name": "Initial Salon",
            "category": "SALON",
            "contact_phone": "+919876543210",
            "contact_address": "100 Old Rd"
        }
    )
    assert res_reg.status_code == 201

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "editbiz@example.com", "password": "password123"}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["business_name"] == "Initial Salon"
    assert me_data["category"] == "SALON"
    assert me_data["contact_phone"] == "+919876543210"
    assert me_data["contact_address"] == "100 Old Rd"

    patch_res = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "business_name": "Updated Clinic",
            "category": "CLINIC",
            "contact_phone": "+919876543999",
            "contact_address": "200 New Blvd"
        }
    )
    assert patch_res.status_code == 200
    patch_data = patch_res.json()
    assert patch_data["business_name"] == "Updated Clinic"
    assert patch_data["category"] == "CLINIC"
    assert patch_data["contact_phone"] == "+919876543999"
    assert patch_data["contact_address"] == "200 New Blvd"

    me_after = client.get("/api/v1/auth/me", headers=headers)
    assert me_after.status_code == 200
    assert me_after.json()["business_name"] == "Updated Clinic"
    assert me_after.json()["category"] == "CLINIC"

def test_customer_cannot_edit_business_fields(
    client: TestClient,
    customer_auth_headers: Dict[str, str]
) -> None:
    res = client.patch(
        "/api/v1/auth/me",
        headers=customer_auth_headers,
        json={"business_name": "Unauthorized Business Name"}
    )
    assert res.status_code == 403


def test_login_inactive_user_blocked_with_403(
    client: TestClient,
    db: Session,
    customer_user: User
) -> None:
    customer_user.is_active = False
    db.commit()

    res = client.post(
        "/api/v1/auth/login",
        json={"email": customer_user.email, "password": "password123"}
    )
    assert res.status_code == 403
    assert res.json()["detail"] == "Account is inactive"

    res_wrong_pw = client.post(
        "/api/v1/auth/login",
        json={"email": customer_user.email, "password": "wrongpassword"}
    )
    assert res_wrong_pw.status_code == 401
