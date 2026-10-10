from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_returns_ok_and_request_id() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]


def test_http_errors_use_common_response_format() -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "http_error",
        "message": "Not Found",
    }
    assert response.json()["request_id"] == response.headers["x-request-id"]
