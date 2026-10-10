from dataclasses import replace
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.database import Database
from backend.app.settings import DEFAULT_DATABASE_PATH, Settings
from backend.tests.auth_helpers import authorization_headers


def test_database_path_is_configurable(monkeypatch, tmp_path) -> None:
    configured_path = tmp_path / "custom" / "backend.sqlite3"
    monkeypatch.setenv("BACKEND_DB_PATH", str(configured_path))

    assert Settings.from_environment().database_path == configured_path
    assert DEFAULT_DATABASE_PATH == (
        Path(main.__file__).resolve().parents[1] / "data" / "app.db"
    )


def test_database_initialization_preserves_existing_support_records(tmp_path) -> None:
    database_path = tmp_path / "existing.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE support_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                facility_id TEXT NOT NULL,
                requester_name TEXT NOT NULL,
                contact TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                request_type TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """INSERT INTO support_requests
               (facility_id, requester_name, contact, requested_at, request_type)
               VALUES ('f-1', 'name', 'contact', '2026-10-10', 'companion')"""
        )

    Database(database_path).initialize()

    with sqlite3.connect(database_path) as connection:
        existing = connection.execute(
            "SELECT facility_id, contact, contact_consent FROM support_requests"
        ).fetchone()
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert existing == ("f-1", "contact", 0)
    assert {"support_requests", "field_checks", "users"} <= tables
    Database(database_path).initialize()
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM support_requests"
        ).fetchone()[0] == 1


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
        test_client.auth_headers = {
            role: authorization_headers(test_client, role)
            for role in ("citizen", "field_worker", "admin")
        }
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
        "/api/v1/support-requests",
        json=support_request("mobility"),
        headers=client.auth_headers["citizen"],
    )

    assert response.status_code == 201
    created = response.json()
    assert created["id"] > 0
    assert created["facility_id"] == "facility-123"
    assert created["request_type"] == "mobility"
    assert created["status"] == "pending"
    assert created["requested_at"] == "2026-10-10T10:00:00+09:00"

    listed = client.get(
        "/api/v1/support-requests?status=pending",
        headers=client.auth_headers["admin"],
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [created["id"]]
    assert client.get(
        "/api/v1/support-requests?status=approved",
        headers=client.auth_headers["admin"],
    ).json() == []


def test_invalid_support_request_type_uses_common_error_response(client) -> None:
    response = client.post(
        "/api/v1/support-requests",
        json=support_request("automatic_match"),
        headers=client.auth_headers["citizen"],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"]
    assert client.get(
        "/api/v1/support-requests", headers=client.auth_headers["admin"]
    ).json() == []


def test_missing_support_request_returns_common_404(client) -> None:
    response = client.get(
        "/api/v1/support-requests/999999",
        headers=client.auth_headers["admin"],
    )

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
    response = client.post(
        "/api/v1/field-checks",
        json=payload,
        headers=client.auth_headers["field_worker"],
    )

    assert response.status_code == 201
    created = response.json()
    assert created["cell_id"] == payload["cell_id"]
    assert created["checklist"] == payload["checklist"]
    assert created["checked_at"] == payload["checked_at"]

    listed = client.get(
        "/api/v1/field-checks",
        params={"cell_id": payload["cell_id"]},
        headers=client.auth_headers["field_worker"],
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == created["id"]
    assert client.get(
        "/api/v1/field-checks",
        params={"cell_id": "other-cell"},
        headers=client.auth_headers["field_worker"],
    ).json() == []


def test_invalid_field_check_payload_uses_common_error_response(client) -> None:
    response = client.post(
        "/api/v1/field-checks",
        json={
            "cell_id": " ",
            "checklist": {},
            "checked_at": "not-a-date",
        },
        headers=client.auth_headers["field_worker"],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_support_contact_is_not_written_to_request_logs(client, capsys) -> None:
    contact = "010-9876-5432"
    response = client.post(
        "/api/v1/support-requests",
        json={
            **support_request(),
            "contact": contact,
            "contact_consent": True,
        },
        headers=client.auth_headers["citizen"],
    )

    assert response.status_code == 201
    assert response.json()["contact"] == contact
    assert contact not in capsys.readouterr().err
