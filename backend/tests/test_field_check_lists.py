from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.auth import password_hash
from backend.tests.auth_helpers import login_as


@pytest.fixture
def client():
    with TestClient(main.app) as test_client:
        yield test_client


def field_check_list(headline: str = "테스트 현장 확인 목록") -> dict:
    return {
        "region": "춘천",
        "headline": headline,
        "created_at": "2026-10-18T01:00:00+09:00",
        "cells": [
            {
                "id": "4026_7935",
                "lat": 37.8546,
                "lon": 127.5753,
                "emd_name": "서면",
                "level": "확인 필요",
                "questions": ["실제로 사람이 사는 집이 있나요?"],
                "order": 1,
                "highlight": False,
            }
        ],
    }


def test_field_worker_list_survives_a_new_login_session() -> None:
    email = f"{uuid4().hex}@example.com"
    password = "test-password-for-field-list"
    payload = field_check_list()

    with TestClient(main.app) as first_device:
        first_device.app.state.database.create_user(
            email, password_hash.hash(password), role="field_worker"
        )
        login = first_device.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert login.status_code == 200
        first_headers = {
            "Authorization": "Bearer " + login.json()["access_token"]
        }

        saved = first_device.put(
            "/api/v1/field-check-list", json=payload, headers=first_headers
        )

    assert saved.status_code == 200
    assert saved.json() == payload

    with TestClient(main.app) as second_device:
        login_again = second_device.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert login_again.status_code == 200
        second_headers = {
            "Authorization": "Bearer " + login_again.json()["access_token"]
        }
        retrieved = second_device.get(
            "/api/v1/field-check-list", headers=second_headers
        )

    assert retrieved.status_code == 200
    assert retrieved.json() == payload


def test_independent_sessions_merge_uploaded_lists_and_refresh_duplicate_cells() -> None:
    email = f"{uuid4().hex}@example.com"
    password = "test-password-for-field-list"
    first_file = {
        **field_check_list("첫 번째 테스트 목록"),
        "cells": [
            field_check_list()["cells"][0] | {"id": "cell-a", "order": 1},
            field_check_list()["cells"][0] | {"id": "cell-shared", "order": 2},
        ],
    }
    second_file = {
        **field_check_list("두 번째 테스트 목록"),
        "cells": [
            field_check_list()["cells"][0]
            | {
                "id": "cell-shared",
                "emd_name": "갱신된 동네",
                "questions": ["새 파일의 질문"],
                "order": 1,
            },
            field_check_list()["cells"][0] | {"id": "cell-b", "order": 2},
        ],
    }

    with TestClient(main.app) as laptop:
        laptop.app.state.database.create_user(
            email, password_hash.hash(password), role="field_worker"
        )
        login = laptop.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert login.status_code == 200
        laptop_headers = {
            "Authorization": "Bearer " + login.json()["access_token"]
        }
        first_save = laptop.put(
            "/api/v1/field-check-list",
            json=first_file,
            headers=laptop_headers,
        )
        assert first_save.status_code == 200
        record = laptop.post(
            "/api/v1/field-checks",
            json={
                "cell_id": "cell-a",
                "checklist": {"has_residents": "yes"},
                "checked_at": "2026-10-18T01:00:00+09:00",
                "note": "저장된 현장기록",
            },
            headers=laptop_headers,
        )
        assert record.status_code == 201

    with TestClient(main.app) as phone:
        login_again = phone.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert login_again.status_code == 200
        phone_headers = {
            "Authorization": "Bearer " + login_again.json()["access_token"]
        }
        before_upload = phone.get(
            "/api/v1/field-check-list", headers=phone_headers
        )
        assert before_upload.status_code == 200
        assert {cell["id"] for cell in before_upload.json()["cells"]} == {
            "cell-a",
            "cell-shared",
        }

        second_save = phone.put(
            "/api/v1/field-check-list",
            json=second_file,
            headers=phone_headers,
        )
        assert second_save.status_code == 200
        merged = second_save.json()
        assert [cell["id"] for cell in merged["cells"]] == [
            "cell-a",
            "cell-shared",
            "cell-b",
        ]
        assert merged["cells"][1]["emd_name"] == "갱신된 동네"
        assert merged["cells"][1]["questions"] == ["새 파일의 질문"]
        assert [cell["order"] for cell in merged["cells"]] == [1, 2, 3]

        preserved_record = phone.get(
            "/api/v1/field-checks",
            params={"cell_id": "cell-a"},
            headers=phone_headers,
        )
        assert preserved_record.status_code == 200
        assert preserved_record.json() == [record.json()]

    with TestClient(main.app) as laptop_again:
        login_again = laptop_again.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        laptop_again_headers = {
            "Authorization": "Bearer " + login_again.json()["access_token"]
        }
        after_upload = laptop_again.get(
            "/api/v1/field-check-list", headers=laptop_again_headers
        )

    assert after_upload.status_code == 200
    assert after_upload.json() == merged


def test_field_check_list_access_is_limited_to_each_field_worker(client) -> None:
    first_worker = login_as(client, "field_worker")
    second_worker = login_as(client, "field_worker")
    citizen = login_as(client, "citizen")
    admin = login_as(client, "admin")
    payload = field_check_list()

    saved = client.put(
        "/api/v1/field-check-list", json=payload, headers=first_worker
    )

    assert saved.status_code == 200
    assert client.get(
        "/api/v1/field-check-list", headers=first_worker
    ).json() == payload
    assert client.get(
        "/api/v1/field-check-list", headers=second_worker
    ).json() is None

    second_payload = field_check_list("다른 담당자의 목록")
    second_saved = client.put(
        "/api/v1/field-check-list", json=second_payload, headers=second_worker
    )
    assert second_saved.status_code == 200
    assert client.get(
        "/api/v1/field-check-list", headers=first_worker
    ).json() == payload

    updated_payload = field_check_list("수정된 목록")
    updated = client.put(
        "/api/v1/field-check-list", json=updated_payload, headers=first_worker
    )
    assert updated.status_code == 200
    assert client.get(
        "/api/v1/field-check-list", headers=first_worker
    ).json() == updated_payload
    assert client.get(
        "/api/v1/field-check-list", headers=second_worker
    ).json() == second_payload

    for headers in (citizen, admin):
        assert client.get(
            "/api/v1/field-check-list", headers=headers
        ).status_code == 403
        assert client.put(
            "/api/v1/field-check-list", json=second_payload, headers=headers
        ).status_code == 403
    assert client.get("/api/v1/field-check-list").status_code == 401
    assert client.put(
        "/api/v1/field-check-list", json=payload
    ).status_code == 401


@pytest.mark.parametrize(
    "invalid_case",
    (
        "missing_cells",
        "extra_root_field",
        "extra_cell_field",
        "string_coordinate",
        "naive_created_at",
    ),
)
def test_field_check_list_rejects_invalid_payloads(client, invalid_case: str) -> None:
    payload = field_check_list()
    if invalid_case == "missing_cells":
        del payload["cells"]
    elif invalid_case == "extra_root_field":
        payload["unexpected"] = True
    elif invalid_case == "extra_cell_field":
        payload["cells"][0]["unexpected"] = True
    elif invalid_case == "string_coordinate":
        payload["cells"][0]["lat"] = "37.8546"
    else:
        payload["created_at"] = "2026-10-18T01:00:00"

    headers = login_as(client, "field_worker")
    response = client.put(
        "/api/v1/field-check-list", json=payload, headers=headers
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert client.get("/api/v1/field-check-list", headers=headers).json() is None
