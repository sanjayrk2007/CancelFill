from typing import Dict
from fastapi.testclient import TestClient
from app.models import User

def test_register_customer_and_business(client: TestClient) -> None:
    res_cust = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newcust@example.com",
            "password": "securepass123",
            "name": "New Customer",
            "role": "CUSTOMER"
        }
    )
    assert res_cust.status_code == 201
    cust_data = res_cust.json()
    assert cust_data["email"] == "newcust@example.com"
    assert cust_data["role"] == "CUSTOMER"
    assert "id" in cust_data

    res_biz = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newbiz@example.com",
            "password": "securepass123",
            "name": "New Business",
            "role": "BUSINESS"
        }
    )
    assert res_biz.status_code == 201
    biz_data = res_biz.json()
    assert biz_data["email"] == "newbiz@example.com"
    assert biz_data["role"] == "BUSINESS"

def test_register_duplicate_email(client: TestClient) -> None:
    payload = {
        "email": "dup@example.com",
        "password": "pass",
        "name": "User 1",
        "role": "CUSTOMER"
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
            "role": "CUSTOMER"
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
            "role": "BUSINESS"
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
