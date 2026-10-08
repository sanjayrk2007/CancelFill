import os

os.environ.setdefault("SCHEDULER_ENABLED", "false")

import pytest
from typing import Generator, Dict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import User, UserRole
from app.security import hash_password, create_access_token

test_db_url = os.getenv("TEST_DATABASE_URL")

def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "concurrency: PostgreSQL-only race-condition tests that use real parallel sessions",
    )

if test_db_url:
    connect_args = {}
    if test_db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(test_db_url, connect_args=connect_args)
else:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function", autouse=True)
def setup_db() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db(setup_db: None) -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def business_user(db: Session) -> User:
    user = User(
        email="biz@example.com",
        name="Business Owner",
        password_hash=hash_password("password123"),
        role=UserRole.BUSINESS.value
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def other_business_user(db: Session) -> User:
    user = User(
        email="other_biz@example.com",
        name="Other Business Owner",
        password_hash=hash_password("password123"),
        role=UserRole.BUSINESS.value
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def customer_user(db: Session) -> User:
    user = User(
        email="cust1@example.com",
        name="Customer One",
        password_hash=hash_password("password123"),
        role=UserRole.CUSTOMER.value
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def customer_user_2(db: Session) -> User:
    user = User(
        email="cust2@example.com",
        name="Customer Two",
        password_hash=hash_password("password123"),
        role=UserRole.CUSTOMER.value
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def other_customer_user(db: Session) -> User:
    user = User(
        email="other_cust@example.com",
        name="Other Customer",
        password_hash=hash_password("password123"),
        role=UserRole.CUSTOMER.value
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def business_auth_headers(business_user: User) -> Dict[str, str]:
    token = create_access_token({"sub": business_user.id, "email": business_user.email, "role": business_user.role})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def other_business_auth_headers(other_business_user: User) -> Dict[str, str]:
    token = create_access_token({"sub": other_business_user.id, "email": other_business_user.email, "role": other_business_user.role})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def customer_auth_headers(customer_user: User) -> Dict[str, str]:
    token = create_access_token({"sub": customer_user.id, "email": customer_user.email, "role": customer_user.role})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def customer_2_auth_headers(customer_user_2: User) -> Dict[str, str]:
    token = create_access_token({"sub": customer_user_2.id, "email": customer_user_2.email, "role": customer_user_2.role})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def other_customer_auth_headers(other_customer_user: User) -> Dict[str, str]:
    token = create_access_token({"sub": other_customer_user.id, "email": other_customer_user.email, "role": other_customer_user.role})
    return {"Authorization": f"Bearer {token}"}
