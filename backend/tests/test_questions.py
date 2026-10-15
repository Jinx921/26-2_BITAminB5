import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from fastapi.testclient import TestClient

from agent.orchestrator import Orchestrator as AgentOrchestrator
from agent.screen import CITIZEN_NOTICE
from backend.app import main
from backend.tests.auth_helpers import authorization_headers


class StubEngine:
    def __init__(self) -> None:
        self.tool_names: list[str] = []


class StubOrchestrator:
    instances = []

    def __init__(self, engine, mode: str) -> None:
        self.engine = engine
        self.mode = mode
        self.calls = []
        self.instances.append(self)

    def ask(self, question: str, location: dict | None = None):
        self.calls.append((question, location))
        display = {"headline": f"{self.mode} response", "map": None}
        screen = {
            "display": display,
            "internal": {
                "tool_trace": ["private tool trace"],
                "verification": "private verification",
                "location": location,
            },
        }
        return screen, object()


def prepare_stub_runtime(monkeypatch) -> list[StubEngine]:
    engines = []
    StubOrchestrator.instances = []

    def make_engine():
        engine = StubEngine()
        engines.append(engine)
        return engine

    monkeypatch.setattr(main, "LiveEngine", make_engine)
    monkeypatch.setattr(main, "Orchestrator", StubOrchestrator)
    return engines


def test_mode_orchestrators_share_one_engine_and_are_reused(monkeypatch) -> None:
    engines = prepare_stub_runtime(monkeypatch)

    with TestClient(main.app) as client:
        admin_payload = {"mode": "admin", "question": "관리자 질문"}
        admin_headers = authorization_headers(client, "admin")
        assert client.post(
            "/api/v1/questions", json=admin_payload, headers=admin_headers
        ).status_code == 200
        assert client.post(
            "/api/v1/questions", json=admin_payload, headers=admin_headers
        ).status_code == 200
        citizen_payload = {
            "mode": "citizen",
            "question": "주변 시설을 알려줘",
            "location": {"lat": 37.88, "lon": 127.73},
        }
        response = client.post(
            "/api/v1/questions",
            json=citizen_payload,
            headers=authorization_headers(client, "citizen"),
        )

    assert len(engines) == 1
    assert len(StubOrchestrator.instances) == 2
    admin, citizen = StubOrchestrator.instances
    assert admin.mode == "admin" and citizen.mode == "citizen"
    assert admin.engine is engines[0] and citizen.engine is engines[0]
    assert len(admin.calls) == 2
    assert citizen.calls == [
        ("주변 시설을 알려줘", {"lat": 37.88, "lon": 127.73})
    ]
    assert response.json() == {"headline": "citizen response", "map": None}


def test_response_and_logs_do_not_expose_internal_or_location(
    monkeypatch, caplog
) -> None:
    prepare_stub_runtime(monkeypatch)
    question = "비공개질문-9c71"
    latitude, longitude = 37.881234, 127.729876

    with caplog.at_level(logging.INFO, logger="backend.api"):
        with TestClient(main.app) as client:
            response = client.post(
                "/api/v1/questions",
                json={
                    "mode": "citizen",
                    "question": question,
                    "location": {"lat": latitude, "lon": longitude},
                },
                headers=authorization_headers(client, "citizen"),
            )

    assert response.json() == {"headline": "citizen response", "map": None}
    assert "internal" not in response.text
    assert "tool_trace" not in response.text
    assert "verification" not in response.text
    assert question not in caplog.text
    assert str(latitude) not in caplog.text
    assert str(longitude) not in caplog.text


class NoCallClient:
    class Messages:
        def create(self, **kwargs):
            raise AssertionError("missing citizen location must not call Anthropic")

    messages = Messages()


def test_citizen_without_location_returns_guidance_without_anthropic(
    monkeypatch,
) -> None:
    engines = []

    def make_engine():
        engine = StubEngine()
        engines.append(engine)
        return engine

    monkeypatch.setattr(main, "LiveEngine", make_engine)
    monkeypatch.setattr(
        main,
        "Orchestrator",
        lambda engine, mode: AgentOrchestrator(
            engine, mode=mode, client=NoCallClient()
        ),
    )

    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/questions",
            json={"mode": "citizen", "question": "주변 시설을 알려줘"},
            headers=authorization_headers(client, "citizen"),
        )

    assert response.status_code == 200
    assert response.json()["headline"] == CITIZEN_NOTICE["no_location"]
    assert "internal" not in response.text
    assert len(engines) == 1


def test_slow_orchestrator_does_not_block_event_loop(monkeypatch) -> None:
    started = Event()
    release = Event()

    class SlowOrchestrator:
        def __init__(self, engine, mode: str) -> None:
            self.mode = mode

        def ask(self, question: str, location: dict | None = None):
            started.set()
            if not release.wait(timeout=5):
                raise TimeoutError("test did not release the blocking ask")
            return {"display": {"headline": "done"}, "internal": {}}, object()

    monkeypatch.setattr(main, "LiveEngine", StubEngine)
    monkeypatch.setattr(main, "Orchestrator", SlowOrchestrator)

    with TestClient(main.app) as client, ThreadPoolExecutor(max_workers=2) as pool:
        question_future = pool.submit(
            client.post,
            "/api/v1/questions",
            json={"mode": "admin", "question": "오래 걸리는 질문"},
            headers=authorization_headers(client, "admin"),
        )
        assert started.wait(timeout=2)
        health_future = pool.submit(client.get, "/health")
        try:
            assert health_future.result(timeout=2).status_code == 200
        finally:
            release.set()
        assert question_future.result(timeout=2).json() == {"headline": "done"}
