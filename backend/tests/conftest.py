from dataclasses import replace

import pytest

from backend.app import main
from backend.app.settings import DEVELOPMENT_ALLOWED_ORIGINS


@pytest.fixture(autouse=True)
def isolated_backend_runtime(monkeypatch, tmp_path):
    monkeypatch.setattr(
        main,
        "settings",
        replace(
            main.settings,
            database_path=tmp_path / "data" / "test.db",
            allowed_origins=DEVELOPMENT_ALLOWED_ORIGINS,
        ),
    )
    monkeypatch.setattr(main, "LiveEngine", lambda: object())
    monkeypatch.setattr(main, "Orchestrator", lambda engine, mode: object())
