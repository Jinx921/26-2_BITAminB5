import logging
from dataclasses import replace
import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.tests.auth_helpers import login_as


def test_citizen_registration_and_login_return_jwt() -> None:
    with TestClient(main.app) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={
                "email": "citizen@example.com",
                "password": "strong-test-password",
            },
        )
        assert registration.status_code == 201
        assert registration.json()["role"] == "citizen"
        assert "password_hash" not in registration.json()
        with sqlite3.connect(client.app.state.database.path) as connection:
            stored_hash = connection.execute(
                "SELECT password_hash FROM users WHERE email = ?",
                ("citizen@example.com",),
            ).fetchone()[0]
        assert stored_hash != "strong-test-password"
        assert stored_hash.startswith("$argon2")

        login = client.post(
            "/api/v1/auth/login",
            json={
                "email": "citizen@example.com",
                "password": "strong-test-password",
            },
        )

    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["user"]["role"] == "citizen"
    assert login.json()["access_token"]


def test_public_registration_cannot_assign_privileged_role() -> None:
    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "escalation@example.com",
                "password": "strong-test-password",
                "role": "admin",
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
        assert client.app.state.database.get_user_by_email(
            "escalation@example.com"
        ) is None


def test_login_failure_does_not_reveal_whether_email_exists() -> None:
    with TestClient(main.app) as client:
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "known@example.com",
                "password": "strong-test-password",
            },
        )
        known = client.post(
            "/api/v1/auth/login",
            json={"email": "known@example.com", "password": "wrong-password"},
        )
        unknown = client.post(
            "/api/v1/auth/login",
            json={"email": "unknown@example.com", "password": "wrong-password"},
        )

    assert known.status_code == unknown.status_code == 401
    assert known.json()["error"] == unknown.json()["error"]
    assert known.json()["error"]["message"] == "Invalid email or password"


def test_unauthenticated_api_returns_common_401() -> None:
    with TestClient(main.app) as client:
        protected_responses = [
            client.get("/api/v1/field-checks?cell_id=cell-1"),
            client.post(
                "/api/v1/questions",
                json={"mode": "admin", "question": "no token"},
            ),
            client.post(
                "/api/v1/support-requests",
                json={
                    "facility_id": "facility-1",
                    "requester_name": "Requester",
                    "requested_at": "2026-10-10T10:00:00Z",
                    "request_type": "companion",
                },
            ),
        ]
        invalid_token = client.get(
            "/api/v1/field-checks?cell_id=cell-1",
            headers={"Authorization": "Bearer malformed-token"},
        )

    assert all(response.status_code == 401 for response in protected_responses)
    assert all(
        response.json()["error"]["code"] == "unauthorized"
        for response in protected_responses
    )
    assert protected_responses[0].headers["www-authenticate"] == "Bearer"
    assert invalid_token.status_code == 401
    assert invalid_token.json()["error"]["code"] == "unauthorized"


def test_incorrect_role_gets_403() -> None:
    with TestClient(main.app) as client:
        headers = login_as(client, "citizen")
        response = client.post(
            "/api/v1/field-checks",
            headers=headers,
            json={
                "cell_id": "cell-1",
                "checklist": {},
                "checked_at": "2026-10-10T10:00:00Z",
            },
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_question_mode_is_forced_by_authenticated_role(monkeypatch) -> None:
    calls = []

    class SpyOrchestrator:
        def __init__(self, engine, mode: str) -> None:
            self.mode = mode

        def ask(self, question, location=None):
            calls.append((self.mode, question))
            return {"display": {"mode": self.mode}, "internal": {"secret": True}}, object()

    monkeypatch.setattr(main, "Orchestrator", SpyOrchestrator)
    with TestClient(main.app) as client:
        citizen_headers = login_as(client, "citizen")
        admin_headers = login_as(client, "admin")
        citizen_response = client.post(
            "/api/v1/questions",
            headers=citizen_headers,
            json={
                "mode": "admin",
                "question": "citizen cannot claim admin",
                "location": {"lat": 37.88, "lon": 127.73},
            },
        )
        admin_response = client.post(
            "/api/v1/questions",
            headers=admin_headers,
            json={"mode": "citizen", "question": "admin remains admin"},
        )

    assert citizen_response.json() == {"mode": "citizen"}
    assert admin_response.json() == {"mode": "admin"}
    assert calls == [
        ("citizen", "citizen cannot claim admin"),
        ("admin", "admin remains admin"),
    ]
    assert "internal" not in citizen_response.text


def test_support_contact_requires_explicit_consent_and_is_not_logged(capsys) -> None:
    with TestClient(main.app) as client:
        headers = login_as(client, "citizen")
        without_consent = client.post(
            "/api/v1/support-requests",
            headers=headers,
            json={
                "facility_id": "facility-1",
                "requester_name": "Requester",
                "contact": "private-contact-without-consent",
                "requested_at": "2026-10-10T10:00:00Z",
                "request_type": "companion",
            },
        )
        with_consent = client.post(
            "/api/v1/support-requests",
            headers=headers,
            json={
                "facility_id": "facility-2",
                "requester_name": "Requester",
                "contact": "consented-contact-value",
                "contact_consent": True,
                "requested_at": "2026-10-10T10:00:00Z",
                "request_type": "mobility",
            },
        )

    assert without_consent.status_code == with_consent.status_code == 201
    assert without_consent.json()["contact"] == ""
    assert without_consent.json()["contact_consent"] is False
    assert with_consent.json()["contact"] == "consented-contact-value"
    assert with_consent.json()["contact_consent"] is True
    output = capsys.readouterr().err
    assert "private-contact-without-consent" not in output
    assert "consented-contact-value" not in output


def test_only_admin_can_read_and_change_support_request_status() -> None:
    with TestClient(main.app) as client:
        citizen = login_as(client, "citizen")
        created = client.post(
            "/api/v1/support-requests",
            headers=citizen,
            json={
                "facility_id": "facility-1",
                "requester_name": "Requester",
                "requested_at": "2026-10-10T10:00:00Z",
                "request_type": "companion",
            },
        )
        request_id = created.json()["id"]
        denied = client.patch(
            f"/api/v1/support-requests/{request_id}/status",
            headers=citizen,
            json={"status": "approved"},
        )
        denied_list = client.get("/api/v1/support-requests", headers=citizen)

        admin = login_as(client, "admin")
        approved = client.patch(
            f"/api/v1/support-requests/{request_id}/status",
            headers=admin,
            json={"status": "approved"},
        )
        listed = client.get("/api/v1/support-requests?status=approved", headers=admin)

    assert denied.status_code == denied_list.status_code == 403
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert listed.json()[0]["id"] == request_id


def test_field_worker_cannot_use_question_api() -> None:
    with TestClient(main.app) as client:
        worker = login_as(client, "field_worker")
        response = client.post(
            "/api/v1/questions",
            headers=worker,
            json={"mode": "admin", "question": "not permitted"},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_production_requires_configured_jwt_secret(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        main,
        "settings",
        replace(
            main.settings,
            environment="production",
            jwt_secret=None,
            database_path=tmp_path / "must-not-be-created.db",
        ),
    )

    with pytest.raises(RuntimeError, match="BACKEND_JWT_SECRET"):
        with TestClient(main.app):
            pass

    assert not (tmp_path / "must-not-be-created.db").exists()


def test_production_rejects_short_jwt_secret(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        main,
        "settings",
        replace(
            main.settings,
            environment="production",
            jwt_secret="short",
            database_path=tmp_path / "must-not-be-created.db",
        ),
    )

    with pytest.raises(RuntimeError, match="at least 32 characters"):
        with TestClient(main.app):
            pass

    assert not (tmp_path / "must-not-be-created.db").exists()


def test_field_worker_can_create_and_read_field_checks_only() -> None:
    with TestClient(main.app) as client:
        worker = login_as(client, "field_worker")
        citizen = login_as(client, "citizen")
        payload = {
            "cell_id": "cell-1",
            "checklist": {"visited": True},
            "checked_at": "2026-10-10T10:00:00Z",
        }
        created = client.post("/api/v1/field-checks", headers=worker, json=payload)
        listed = client.get(
            "/api/v1/field-checks?cell_id=cell-1", headers=worker
        )
        citizen_denied = client.post(
            "/api/v1/field-checks", headers=citizen, json=payload
        )

    assert created.status_code == 201
    assert listed.status_code == 200 and len(listed.json()) == 1
    assert citizen_denied.status_code == 403


def test_authentication_secrets_are_not_logged(caplog) -> None:
    password = "unique-secret-test-password"
    with caplog.at_level(logging.INFO, logger="backend.api"):
        with TestClient(main.app) as client:
            response = client.post(
                "/api/v1/auth/register",
                json={"email": "private@example.com", "password": password},
            )
            client.post(
                "/api/v1/auth/login",
                json={"email": "private@example.com", "password": password},
            )
            client.get(
                "/api/v1/field-checks?cell_id=private",
                headers={"Authorization": "Bearer secret-auth-header"},
            )

    assert response.status_code == 201
    assert password not in caplog.text
    assert "private@example.com" not in caplog.text
    assert "secret-auth-header" not in caplog.text
