from typing import Generator
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db

class BrokenSession:
    def execute(self, *args: object, **kwargs: object) -> None:
        raise Exception("Database failure")

def test_health_check_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_health_check_unreachable(client: TestClient) -> None:
    def override_broken_db() -> Generator[BrokenSession, None, None]:
        yield BrokenSession()

    app.dependency_overrides[get_db] = override_broken_db
    try:
        response = client.get("/health")
        assert response.status_code == 503
        assert response.json() == {"detail": "Database unreachable"}
    finally:
        app.dependency_overrides.clear()

def test_cors_headers(client: TestClient) -> None:
    response = client.options(
        "/api/v1/slots",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
