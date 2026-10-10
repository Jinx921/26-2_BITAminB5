from fastapi.testclient import TestClient

from backend.app import main
from backend.app.auth import password_hash


def test_role_workflow_across_questions_support_and_field_signals(
    monkeypatch,
) -> None:
    question_calls: list[tuple[str, str, dict | None]] = []

    class StubOrchestrator:
        def __init__(self, engine, mode: str) -> None:
            self.mode = mode

        def ask(self, question: str, location: dict | None = None):
            question_calls.append((self.mode, question, location))
            return (
                {
                    "display": {"headline": "Mocked answer", "map": None},
                    "internal": {"tool_trace": ["must not be returned"]},
                },
                object(),
            )

    monkeypatch.setattr(main, "Orchestrator", StubOrchestrator)

    citizen_email = "workflow-citizen@example.com"
    citizen_password = "workflow-citizen-password"
    support_private_values = [
        (
            f"Workflow Requester {index}",
            f"workflow-private-contact-{index}",
            f"workflow-private-note-{index}",
        )
        for index in range(4)
    ]
    field_note = "workflow-private-field-note"
    checklist_label = "workflow-private-checklist-label"

    with TestClient(main.app) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": citizen_email, "password": citizen_password},
        )
        assert registration.status_code == 201
        assert registration.json()["role"] == "citizen"

        citizen_login = client.post(
            "/api/v1/auth/login",
            json={"email": citizen_email, "password": citizen_password},
        )
        assert citizen_login.status_code == 200
        citizen_headers = {
            "Authorization": f"Bearer {citizen_login.json()['access_token']}"
        }
        worker_email = "workflow-field-worker@example.com"
        worker_password = "workflow-field-worker-password"
        client.app.state.database.create_user(
            worker_email,
            password_hash.hash(worker_password),
            role="field_worker",
        )
        worker_login = client.post(
            "/api/v1/auth/login",
            json={"email": worker_email, "password": worker_password},
        )
        assert worker_login.status_code == 200
        assert worker_login.json()["user"]["role"] == "field_worker"
        worker_headers = {
            "Authorization": f"Bearer {worker_login.json()['access_token']}"
        }

        admin_password = "workflow-admin-password"
        client.app.state.database.create_user(
            "workflow-admin@example.com",
            password_hash.hash(admin_password),
            role="admin",
        )
        admin_login = client.post(
            "/api/v1/auth/login",
            json={
                "email": "workflow-admin@example.com",
                "password": admin_password,
            },
        )
        assert admin_login.status_code == 200
        admin_headers = {
            "Authorization": f"Bearer {admin_login.json()['access_token']}"
        }

        question = client.post(
            "/api/v1/questions",
            headers=citizen_headers,
            json={
                "mode": "admin",
                "question": "Find nearby accessible facilities",
                "location": {"lat": 37.88, "lon": 127.73},
            },
        )

        created_requests = []
        for name, contact, note in support_private_values:
            created = client.post(
                "/api/v1/support-requests",
                headers=citizen_headers,
                json={
                    "facility_id": "workflow-facility",
                    "requester_name": name,
                    "contact": contact,
                    "contact_consent": True,
                    "requested_at": "2026-10-10T10:00:00Z",
                    "request_type": "companion",
                    "note": note,
                },
            )
            assert created.status_code == 201
            assert created.json()["contact"] == contact
            assert created.json()["contact_consent"] is True
            created_requests.append(created.json())

        field_check = client.post(
            "/api/v1/field-checks",
            headers=worker_headers,
            json={
                "cell_id": "workflow-cell",
                "checklist": {checklist_label: True, "accessible": True},
                "checked_at": "2026-10-10T11:00:00Z",
                "note": field_note,
            },
        )

        support_list = client.get(
            "/api/v1/support-requests", headers=admin_headers
        )
        changed_status = client.patch(
            f"/api/v1/support-requests/{created_requests[0]['id']}/status",
            headers=admin_headers,
            json={"status": "approved"},
        )
        demand_signals = client.get(
            "/api/v1/admin/demand-signals", headers=admin_headers
        )
        field_summary = client.get(
            "/api/v1/admin/field-feedback-summary", headers=admin_headers
        )

        citizen_admin_responses = [
            client.get("/api/v1/admin/demand-signals", headers=citizen_headers),
            client.get(
                "/api/v1/admin/field-feedback-summary", headers=citizen_headers
            ),
        ]
        worker_admin_responses = [
            client.get("/api/v1/admin/demand-signals", headers=worker_headers),
            client.get(
                "/api/v1/admin/field-feedback-summary", headers=worker_headers
            ),
        ]

    assert question.status_code == 200
    assert question.json() == {"headline": "Mocked answer", "map": None}
    assert "internal" not in question.text
    assert "tool_trace" not in question.text
    assert question_calls == [
        (
            "citizen",
            "Find nearby accessible facilities",
            {"lat": 37.88, "lon": 127.73},
        )
    ]

    assert support_list.status_code == 200
    assert len(support_list.json()) == 4
    assert all(item["status"] == "pending" for item in support_list.json())
    assert changed_status.status_code == 200
    assert changed_status.json()["status"] == "approved"

    assert field_check.status_code == 201
    assert field_check.json()["cell_id"] == "workflow-cell"
    assert demand_signals.status_code == 200
    assert demand_signals.json() == [
        {
            "facility_id": "workflow-facility",
            "request_type": "companion",
            "status": "pending",
            "count": 3,
        }
    ]
    assert field_summary.status_code == 200
    assert field_summary.json() == [
        {
            "cell_id": "workflow-cell",
            "checked_count": 1,
            "checklist_responses": [
                {"item_index": 1, "response_count": 1},
                {"item_index": 2, "response_count": 1},
            ],
        }
    ]

    assert all(response.status_code == 403 for response in citizen_admin_responses)
    assert all(
        response.json()["error"]["code"] == "forbidden"
        for response in citizen_admin_responses
    )
    assert all(response.status_code == 403 for response in worker_admin_responses)
    assert all(
        response.json()["error"]["code"] == "forbidden"
        for response in worker_admin_responses
    )

    anonymous_responses = demand_signals.text + field_summary.text
    for private_value in (
        citizen_email,
        "workflow-admin@example.com",
        "workflow-field-worker@example.com",
        *(value for record in support_private_values for value in record),
        field_note,
        checklist_label,
    ):
        assert private_value not in anonymous_responses
