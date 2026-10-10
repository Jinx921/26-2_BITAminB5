from fastapi.testclient import TestClient

from backend.app import main
from backend.app.main import app
from backend.tests.auth_helpers import authorization_headers

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


def test_question_validation_uses_common_error_format(monkeypatch) -> None:
    monkeypatch.setattr(main, "LiveEngine", lambda: object())
    monkeypatch.setattr(main, "Orchestrator", lambda engine, mode: object())
    with TestClient(app) as live_client:
        headers = authorization_headers(live_client, "citizen")
        for payload in (
            {"mode": "unknown", "question": "질문"},
            {"mode": "admin", "question": "   "},
            {"mode": "admin"},
            {"mode": "citizen", "question": "질문", "location": {"lat": 91, "lon": 0}},
            {"mode": "citizen", "question": "질문", "location": {"lat": 37}},
        ):
            response = live_client.post(
                "/api/v1/questions", json=payload, headers=headers
            )

            assert response.status_code == 422
            assert response.json()["error"]["code"] == "validation_error"
            assert response.json()["request_id"] == response.headers["x-request-id"]
        admin_location = live_client.post(
            "/api/v1/questions",
            headers=authorization_headers(live_client, "admin"),
            json={
                "mode": "admin",
                "question": "질문",
                "location": {"lat": 37, "lon": 127},
            },
        )
        assert admin_location.status_code == 422
        assert admin_location.json()["error"]["code"] == "validation_error"
