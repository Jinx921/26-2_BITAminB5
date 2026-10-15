import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event

import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.settings import Settings
from backend.tests.auth_helpers import authorization_headers


class StubOrchestrator:
    def __init__(self, engine, mode: str) -> None:
        self.mode = mode

    def ask(self, question: str, location: dict | None = None):
        return (
            {"display": {"mode": self.mode}, "internal": {"secret": True}},
            object(),
        )


def test_question_limits_are_independent_by_role_and_return_retry_after(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        main,
        "settings",
        replace(
            main.settings,
            citizen_question_rate_limit=1,
            admin_question_rate_limit=2,
            question_rate_window_seconds=60,
        ),
    )
    monkeypatch.setattr(main, "Orchestrator", StubOrchestrator)

    with TestClient(main.app) as client:
        citizen_headers = authorization_headers(client, "citizen")
        admin_headers = authorization_headers(client, "admin")

        citizen_success = client.post(
            "/api/v1/questions",
            headers=citizen_headers,
            json={"mode": "citizen", "question": "first citizen question"},
        )
        citizen_limited = client.post(
            "/api/v1/questions",
            headers=citizen_headers,
            json={"mode": "citizen", "question": "second citizen question"},
        )
        admin_first = client.post(
            "/api/v1/questions",
            headers=admin_headers,
            json={"mode": "admin", "question": "first admin question"},
        )
        admin_second = client.post(
            "/api/v1/questions",
            headers=admin_headers,
            json={"mode": "admin", "question": "second admin question"},
        )
        admin_limited = client.post(
            "/api/v1/questions",
            headers=admin_headers,
            json={"mode": "admin", "question": "third admin question"},
        )

    assert citizen_success.status_code == 200
    assert citizen_limited.status_code == 429
    assert citizen_limited.json()["error"]["code"] == "rate_limit_exceeded"
    assert 1 <= int(citizen_limited.headers["retry-after"]) <= 60
    assert admin_first.status_code == admin_second.status_code == 200
    assert admin_limited.status_code == 429
    assert admin_limited.json()["error"]["code"] == "rate_limit_exceeded"
    assert 1 <= int(admin_limited.headers["retry-after"]) <= 60
    assert "request_id" in citizen_limited.json()


def test_question_rate_limit_storage_and_logs_exclude_request_data(
    monkeypatch, caplog
) -> None:
    monkeypatch.setattr(main, "Orchestrator", StubOrchestrator)
    question = "private-question-content-7f1a"
    latitude = 37.881234
    longitude = 127.729876

    with caplog.at_level(logging.INFO, logger="backend.api"):
        with TestClient(main.app) as client:
            headers = authorization_headers(client, "citizen")
            token = headers["Authorization"].removeprefix("Bearer ")
            response = client.post(
                "/api/v1/questions",
                headers=headers,
                json={
                    "mode": "citizen",
                    "question": question,
                    "location": {"lat": latitude, "lon": longitude},
                },
            )
            with sqlite3.connect(client.app.state.database.path) as connection:
                columns = [
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(question_rate_limit_events)"
                    )
                ]
                events = connection.execute(
                    "SELECT user_id, requested_at FROM question_rate_limit_events"
                ).fetchall()
                database_dump = "\n".join(
                    str(row)
                    for table in (
                        "question_rate_limit_events",
                        "support_requests",
                        "field_checks",
                    )
                    for row in connection.execute(f"SELECT * FROM {table}")
                )

    assert response.status_code == 200
    assert columns == ["user_id", "requested_at"]
    assert len(events) == 1
    assert isinstance(events[0][0], int)
    assert isinstance(events[0][1], float)
    assert question not in database_dump
    assert str(latitude) not in database_dump
    assert str(longitude) not in database_dump
    for private_value in (question, str(latitude), str(longitude), token):
        assert private_value not in caplog.text


def test_expired_question_rate_limit_events_are_pruned(tmp_path) -> None:
    from backend.app.database import Database

    database = Database(tmp_path / "limits.db")
    database.initialize()
    assert database.record_question_request(1, 100.0, 60, 2) is None
    assert database.record_question_request(1, 110.0, 60, 2) is None
    assert database.record_question_request(2, 150.0, 60, 2) is None

    assert database.record_question_request(2, 200.0, 60, 2) is None

    with sqlite3.connect(database.path) as connection:
        rows = connection.execute(
            "SELECT user_id, requested_at FROM question_rate_limit_events "
            "ORDER BY user_id, requested_at"
        ).fetchall()
    assert rows == [(2, 150.0), (2, 200.0)]


def test_question_calls_are_rejected_when_server_capacity_is_full(
    monkeypatch,
) -> None:
    entered = Event()
    release = Event()

    class SlowOrchestrator:
        def __init__(self, engine, mode: str) -> None:
            self.mode = mode

        def ask(self, question: str, location: dict | None = None):
            entered.set()
            if not release.wait(timeout=5):
                raise TimeoutError("test did not release the mocked question")
            return {"display": {"mode": self.mode}, "internal": {}}, object()

    monkeypatch.setattr(
        main,
        "settings",
        replace(main.settings, question_max_concurrency=1),
    )
    monkeypatch.setattr(main, "Orchestrator", SlowOrchestrator)

    with TestClient(main.app) as client, ThreadPoolExecutor(max_workers=2) as pool:
        headers = authorization_headers(client, "citizen")
        first_call = pool.submit(
            client.post,
            "/api/v1/questions",
            headers=headers,
            json={"mode": "citizen", "question": "first in-flight question"},
        )
        assert entered.wait(timeout=2)
        try:
            overloaded = client.post(
                "/api/v1/questions",
                headers=headers,
                json={"mode": "citizen", "question": "over capacity question"},
            )
        finally:
            release.set()
        completed = first_call.result(timeout=3)

    assert completed.status_code == 200
    assert overloaded.status_code == 503
    assert overloaded.json()["error"]["code"] == "question_capacity_exceeded"
    assert overloaded.headers["retry-after"] == "1"


def test_non_development_requires_explicit_question_rate_limits(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(
        main,
        "settings",
        replace(
            main.settings,
            environment="production",
            jwt_secret="x" * 32,
            allowed_origins=("https://front.example.test",),
            citizen_question_rate_limit=None,
            admin_question_rate_limit=None,
            question_rate_window_seconds=None,
            database_path=tmp_path / "must-not-be-created.db",
        ),
    )

    with pytest.raises(RuntimeError, match="BACKEND_QUESTION_RATE_LIMIT"):
        with TestClient(main.app):
            pass

    assert not (tmp_path / "must-not-be-created.db").exists()


def test_settings_parse_question_limit_environment(monkeypatch) -> None:
    monkeypatch.setenv("BACKEND_ENVIRONMENT", "production")
    monkeypatch.setenv("BACKEND_QUESTION_RATE_LIMIT_CITIZEN", "7")
    monkeypatch.setenv("BACKEND_QUESTION_RATE_LIMIT_ADMIN", "19")
    monkeypatch.setenv("BACKEND_QUESTION_RATE_WINDOW_SECONDS", "90")

    settings = Settings.from_environment()

    assert settings.citizen_question_rate_limit == 7
    assert settings.admin_question_rate_limit == 19
    assert settings.question_rate_window_seconds == 90
    settings.validate_question_rate_limits()


@pytest.mark.parametrize("value", ["0", "-1", "not-an-integer"])
def test_settings_reject_invalid_question_limit_environment(
    monkeypatch, value
) -> None:
    monkeypatch.setenv("BACKEND_QUESTION_RATE_LIMIT_CITIZEN", value)

    with pytest.raises(ValueError, match="BACKEND_QUESTION_RATE_LIMIT_CITIZEN"):
        Settings.from_environment()
