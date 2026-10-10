from fastapi.testclient import TestClient

from backend.app import main
from backend.tests.auth_helpers import authorization_headers


def _support_payload(
    suffix: str,
    *,
    facility_id: str = "facility-aggregate",
    request_type: str = "companion",
    contact_consent: bool = True,
) -> dict:
    return {
        "facility_id": facility_id,
        "requester_name": f"private-name-{suffix}",
        "contact": f"private-contact-{suffix}",
        "contact_consent": contact_consent,
        "requested_at": "2026-10-10T10:00:00Z",
        "request_type": request_type,
        "note": f"private-note-{suffix}",
    }


def test_demand_signals_admin_only_and_suppress_groups_under_three() -> None:
    with TestClient(main.app) as client:
        citizen = authorization_headers(client, "citizen")
        admin = authorization_headers(client, "admin")

        for index in range(2):
            response = client.post(
                "/api/v1/support-requests",
                headers=citizen,
                json=_support_payload(str(index), facility_id="small-facility"),
            )
            assert response.status_code == 201
        for index in range(3):
            response = client.post(
                "/api/v1/support-requests",
                headers=citizen,
                json=_support_payload(
                    f"large-{index}",
                    facility_id="large-facility",
                    request_type="mobility",
                ),
            )
            assert response.status_code == 201

        unauthenticated = client.get("/api/v1/admin/demand-signals")
        forbidden = client.get(
            "/api/v1/admin/demand-signals", headers=citizen
        )
        response = client.get("/api/v1/admin/demand-signals", headers=admin)

    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "unauthorized"
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "forbidden"
    assert response.status_code == 200
    assert response.json() == [
        {
            "facility_id": "large-facility",
            "request_type": "mobility",
            "status": "pending",
            "count": 3,
        }
    ]


def test_demand_signals_exclude_private_request_data(capsys) -> None:
    with TestClient(main.app) as client:
        citizen = authorization_headers(client, "citizen")
        admin = authorization_headers(client, "admin")
        for index in range(3):
            client.post(
                "/api/v1/support-requests",
                headers=citizen,
                json=_support_payload(f"pii-{index}"),
            )
        response = client.get("/api/v1/admin/demand-signals", headers=admin)

    serialized = response.text
    logs = capsys.readouterr().err
    for private_value in (
        "private-name-",
        "private-contact-",
        "private-note-",
        "requester_name",
        "contact",
        "note",
        "email",
    ):
        assert private_value not in serialized
        assert private_value not in logs
    assert set(response.json()[0]) == {
        "facility_id",
        "request_type",
        "status",
        "count",
    }


def test_empty_demand_signals_return_empty_list() -> None:
    with TestClient(main.app) as client:
        admin = authorization_headers(client, "admin")
        response = client.get("/api/v1/admin/demand-signals", headers=admin)

    assert response.status_code == 200
    assert response.json() == []


def test_field_feedback_summary_contains_counts_without_originals_or_notes(
    capsys,
) -> None:
    with TestClient(main.app) as client:
        worker = authorization_headers(client, "field_worker")
        admin = authorization_headers(client, "admin")
        citizen = authorization_headers(client, "citizen")
        for index, checklist in enumerate(
            (
                {"private checklist prompt from name": True, "ramp": True},
                {"private checklist prompt from name": False},
            )
        ):
            created = client.post(
                "/api/v1/field-checks",
                headers=worker,
                json={
                    "cell_id": "cell-privacy",
                    "checklist": checklist,
                    "checked_at": "2026-10-10T10:00:00Z",
                    "note": f"private-field-note-{index}",
                },
            )
            assert created.status_code == 201

        unauthenticated = client.get("/api/v1/admin/field-feedback-summary")
        forbidden = client.get(
            "/api/v1/admin/field-feedback-summary", headers=citizen
        )
        response = client.get(
            "/api/v1/admin/field-feedback-summary", headers=admin
        )

    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "unauthorized"
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "forbidden"
    assert response.status_code == 200
    assert response.json() == [
        {
            "cell_id": "cell-privacy",
            "checked_count": 2,
            "checklist_responses": [
                {"item_index": 1, "response_count": 2},
                {"item_index": 2, "response_count": 1},
            ],
        }
    ]
    serialized = response.text
    logs = capsys.readouterr().err
    for private_value in (
        "private-field-note",
        "private checklist prompt from name",
        "note",
        "author",
        "private-contact",
        "private@example.com",
    ):
        assert private_value not in serialized
        assert private_value not in logs


def test_empty_field_feedback_summary_returns_empty_list() -> None:
    with TestClient(main.app) as client:
        admin = authorization_headers(client, "admin")
        response = client.get(
            "/api/v1/admin/field-feedback-summary", headers=admin
        )

    assert response.status_code == 200
    assert response.json() == []
