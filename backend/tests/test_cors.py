from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.settings import (
    DEVELOPMENT_ALLOWED_ORIGINS,
    Settings,
)


def test_development_origin_configuration_defaults_and_parses(monkeypatch) -> None:
    monkeypatch.setenv("BACKEND_ENVIRONMENT", "development")
    monkeypatch.delenv("BACKEND_ALLOWED_ORIGINS", raising=False)
    defaults = Settings.from_environment()
    assert defaults.allowed_origins == (
        "http://localhost:5173",
        "http://localhost:3000",
    )

    monkeypatch.setenv(
        "BACKEND_ALLOWED_ORIGINS",
        " https://front.example.test, http://localhost:8080 ,,",
    )
    configured = Settings.from_environment()
    assert configured.allowed_origins == (
        "https://front.example.test",
        "http://localhost:8080",
    )


def test_allowed_origin_preflight_and_request_work_without_credentials() -> None:
    with TestClient(main.app) as client:
        preflight = client.options(
            "/api/v1/questions",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        response = client.get(
            "/health", headers={"Origin": "http://localhost:3000"}
        )

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in preflight.headers["access-control-allow-methods"]
    assert "PUT" in preflight.headers["access-control-allow-methods"]
    assert "authorization" in preflight.headers["access-control-allow-headers"].lower()
    assert preflight.headers.get("access-control-allow-credentials") != "true"
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") != "true"


def test_unconfigured_origin_cannot_read_api_responses() -> None:
    with TestClient(main.app) as client:
        response = client.get(
            "/health", headers={"Origin": "https://untrusted.example.test"}
        )
        preflight = client.options(
            "/api/v1/questions",
            headers={
                "Origin": "https://untrusted.example.test",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert "access-control-allow-origin" not in response.headers
    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers


@pytest.mark.parametrize("origins", [(), ("*",), ("https://front.example.test", "*")])
def test_production_rejects_missing_or_wildcard_origins(origins) -> None:
    settings = replace(
        Settings(),
        environment="production",
        allowed_origins=origins,
    )

    with pytest.raises(RuntimeError, match="BACKEND_ALLOWED_ORIGINS"):
        settings.validate_allowed_origins()


def test_production_accepts_explicit_origins() -> None:
    settings = replace(
        Settings(),
        environment="production",
        allowed_origins=("https://front.example.test",),
    )

    settings.validate_allowed_origins()


@pytest.mark.parametrize("origins", [(), ("*",)])
def test_production_refuses_to_start_without_safe_origin_list(
    monkeypatch, tmp_path, origins
) -> None:
    monkeypatch.setattr(
        main,
        "settings",
        replace(
            main.settings,
            environment="production",
            jwt_secret="x" * 32,
            allowed_origins=origins,
            database_path=tmp_path / "must-not-be-created.db",
        ),
    )

    with pytest.raises(RuntimeError, match="BACKEND_ALLOWED_ORIGINS"):
        with TestClient(main.app):
            pass

    assert not (tmp_path / "must-not-be-created.db").exists()


def test_development_origin_defaults_are_localhost_only() -> None:
    assert DEVELOPMENT_ALLOWED_ORIGINS == (
        "http://localhost:5173",
        "http://localhost:3000",
    )
