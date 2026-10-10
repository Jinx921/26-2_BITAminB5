from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.settings import DEFAULT_DATABASE_PATH, Settings


def test_database_path_is_configurable(monkeypatch, tmp_path) -> None:
    configured_path = tmp_path / "custom" / "backend.sqlite3"
    monkeypatch.setenv("BACKEND_DB_PATH", str(configured_path))

    assert Settings.from_environment().database_path == configured_path
    assert DEFAULT_DATABASE_PATH == (
        Path(main.__file__).resolve().parents[1] / "data" / "app.db"
    )


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(
        main,
        "settings",
        replace(main.settings, database_path=tmp_path / "data" / "test.db"),
    )
    monkeypatch.setattr(main, "LiveEngine", lambda: object())
    monkeypatch.setattr(main, "Orchestrator", lambda engine, mode: object())
    with TestClient(main.app) as test_client:
        yield test_client


def support_request(request_type: str = "companion") -> dict:
    return {
        "facility_id": "facility-123",
        "requester_name": "홍길동",
        "contact": "010-1234-5678",
        "requested_at": "2026-10-10T10:00:00+09:00",
        "request_type": request_type,
        "note": "도착 전에 연락 바랍니다",
    }


def test_support_request_create_and_list_with_status_filter(client) -> None:
    response = client.post(
        "/api/v1/support-requests", json=support_request("mobility")
    )

    assert response.status_code == 201
    created = response.json()
    assert created["id"] > 0
    assert created["facility_id"] == "facility-123"
    assert created["request_type"] == "mobility"
    assert created["status"] == "pending"
    assert created["requested_at"] == "2026-10-10T10:00:00+09:00"

    listed = client.get("/api/v1/support-requests?status=pending")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [created["id"]]
    assert client.get("/api/v1/support-requests?status=approved").json() == []


def test_invalid_support_request_type_uses_common_error_response(client) -> None:
    response = client.post(
        "/api/v1/support-requests", json=support_request("automatic_match")
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"]
    assert client.get("/api/v1/support-requests").json() == []


def test_missing_support_request_returns_common_404(client) -> None:
    response = client.get("/api/v1/support-requests/999999")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "http_error",
        "message": "Support request not found",
    }


def test_field_check_create_and_filter_by_cell(client) -> None:
    payload = {
        "cell_id": "4026_7935",
        "checklist": {"accessible": True, "bench": False, "observations": ["계단"]},
        "checked_at": "2026-10-10T11:30:00+09:00",
        "note": "입구에 계단이 있음",
    }
    response = client.post("/api/v1/field-checks", json=payload)

    assert response.status_code == 201
    created = response.json()
    assert created["cell_id"] == payload["cell_id"]
    assert created["checklist"] == payload["checklist"]
    assert created["checked_at"] == payload["checked_at"]

    listed = client.get(
        "/api/v1/field-checks", params={"cell_id": payload["cell_id"]}
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == created["id"]
    assert client.get(
        "/api/v1/field-checks", params={"cell_id": "other-cell"}
    ).json() == []


def test_invalid_field_check_payload_uses_common_error_response(client) -> None:
    response = client.post(
        "/api/v1/field-checks",
        json={
            "cell_id": " ",
            "checklist": {},
            "checked_at": "not-a-date",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_support_contact_is_not_written_to_request_logs(client, capsys) -> None:
    contact = "010-9876-5432"
    response = client.post(
        "/api/v1/support-requests",
        json={**support_request(), "contact": contact},
    )

    assert response.status_code == 201
    assert response.json()["contact"] == contact
    assert contact not in capsys.readouterr().err
