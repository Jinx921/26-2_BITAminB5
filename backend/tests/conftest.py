from dataclasses import replace

import pytest

from backend.app import main


@pytest.fixture(autouse=True)
def isolated_backend_runtime(monkeypatch, tmp_path):
    monkeypatch.setattr(
        main,
        "settings",
        replace(main.settings, database_path=tmp_path / "data" / "test.db"),
    )
    monkeypatch.setattr(main, "LiveEngine", lambda: object())
    monkeypatch.setattr(main, "Orchestrator", lambda engine, mode: object())
