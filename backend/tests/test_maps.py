import json
from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import main
from backend.tests.auth_helpers import login_as

ENGINE_OUT = Path(__file__).resolve().parents[2] / "engine" / "out"


def _create_check(
    client: TestClient,
    cell_id: str,
    checked_at: str,
    checklist: dict[str, str],
) -> None:
    client.app.state.database.create_field_check(
        {
            "cell_id": cell_id,
            "checked_at": checked_at,
            "checklist": checklist,
            "note": "private test note",
        }
    )


def _type_feature(region: str, index: int = 0) -> dict:
    geojson = json.loads(
        (ENGINE_OUT / f"types_{region}.geojson").read_text(encoding="utf-8")
    )
    return geojson["features"][index]


def test_citizen_facility_map_only_returns_facility_properties() -> None:
    with TestClient(main.app) as client:
        headers = login_as(client, "citizen")
        response = client.get(
            "/api/v1/maps/facilities",
            params={"region": "춘천"},
            headers=headers,
        )

    assert response.status_code == 200
    geojson = response.json()
    assert set(geojson) == {"type", "features"}
    assert geojson["type"] == "FeatureCollection"
    assert geojson["features"]
    for feature in geojson["features"]:
        assert set(feature) == {"type", "geometry", "properties"}
        assert set(feature["properties"]) <= {
            "fac_id",
            "name",
            "addr",
            "kind",
            "group",
        }
        assert not {
            "cell_id",
            "type",
            "priority",
            "gap_tag",
            "persistent_months",
            "res_status",
            "covered",
            "field_status",
            "field_checked_at",
            "engine_type",
        } & set(feature["properties"])


def test_citizen_and_field_worker_cannot_read_admin_maps() -> None:
    with TestClient(main.app) as client:
        citizen = login_as(client, "citizen")
        field_worker = login_as(client, "field_worker")
        citizen_response = client.get(
            "/api/v1/admin/maps/types",
            params={"region": "춘천"},
            headers=citizen,
        )
        worker_response = client.get(
            "/api/v1/admin/maps/candidates",
            params={"region": "춘천"},
            headers=field_worker,
        )

    assert citizen_response.status_code == 403
    assert worker_response.status_code == 403


def test_admin_map_selectors_are_allowlisted() -> None:
    with TestClient(main.app) as client:
        headers = login_as(client, "admin")
        invalid_region = client.get(
            "/api/v1/admin/maps/types",
            params={"region": "서울"},
            headers=headers,
        )
        invalid_radius = client.get(
            "/api/v1/admin/maps/placements",
            params={"region": "강남", "radius_m": 2000},
            headers=headers,
        )
        valid_placement = client.get(
            "/api/v1/admin/maps/placements",
            params={"region": "강남", "radius_m": 3000, "sites": 3},
            headers=headers,
        )

    assert invalid_region.status_code == 422
    assert invalid_radius.status_code == 422
    assert valid_placement.status_code == 200


def test_admin_types_use_only_latest_checked_at_record() -> None:
    feature = _type_feature("춘천")
    original_properties = deepcopy(feature["properties"])
    with TestClient(main.app) as client:
        headers = login_as(client, "admin")
        _create_check(
            client,
            feature["properties"]["cell_id"],
            "2026-10-13T14:00:00+09:00",
            {"support_needed": "not_needed"},
        )
        _create_check(
            client,
            feature["properties"]["cell_id"],
            "2026-10-13T06:00:00Z",
            {"support_needed": "unsure"},
        )
        response = client.get(
            "/api/v1/admin/maps/types",
            params={"region": "춘천"},
            headers=headers,
        )

    assert response.status_code == 200
    updated = next(
        item
        for item in response.json()["features"]
        if item["properties"]["cell_id"] == feature["properties"]["cell_id"]
    )
    assert updated["properties"] == original_properties


def test_excluded_has_priority_and_is_hidden_unless_requested() -> None:
    feature = _type_feature("춘천", 1)
    original_properties = feature["properties"]
    with TestClient(main.app) as client:
        headers = login_as(client, "admin")
        _create_check(
            client,
            original_properties["cell_id"],
            "2026-10-13T15:00:00+09:00",
            {"has_residents": "no", "support_needed": "not_needed"},
        )
        hidden = client.get(
            "/api/v1/admin/maps/types",
            params={"region": "춘천"},
            headers=headers,
        )
        shown = client.get(
            "/api/v1/admin/maps/types",
            params={"region": "춘천", "show_excluded": "true"},
            headers=headers,
        )

    assert hidden.status_code == shown.status_code == 200
    assert all(
        item["properties"]["cell_id"] != original_properties["cell_id"]
        for item in hidden.json()["features"]
    )
    excluded = next(
        item
        for item in shown.json()["features"]
        if item["properties"]["cell_id"] == original_properties["cell_id"]
    )
    assert excluded["properties"]["field_status"] == "excluded"
    assert excluded["properties"]["engine_type"] == original_properties["type"]
    assert excluded["properties"]["engine_priority"] == original_properties["priority"]
    assert excluded["properties"]["type"] == original_properties["type"]
    assert excluded["properties"]["priority"] == original_properties["priority"]
    assert excluded["properties"]["field_checked_at"] == "2026-10-13T15:00:00+09:00"


def test_support_not_needed_downgrades_and_keeps_engine_values() -> None:
    feature = _type_feature("강남")
    original_properties = feature["properties"]
    source_path = ENGINE_OUT / "types_강남.geojson"
    original_source = source_path.read_bytes()
    with TestClient(main.app) as client:
        headers = login_as(client, "admin")
        _create_check(
            client,
            original_properties["cell_id"],
            "2026-10-13T15:00:00+09:00",
            {"has_residents": "yes", "support_needed": "not_needed"},
        )
        response = client.get(
            "/api/v1/admin/maps/types",
            params={"region": "강남"},
            headers=headers,
        )

    assert response.status_code == 200
    downgraded = next(
        item
        for item in response.json()["features"]
        if item["properties"]["cell_id"] == original_properties["cell_id"]
    )
    assert downgraded["properties"]["type"] == "관찰형"
    assert downgraded["properties"]["priority"] == 4
    assert downgraded["properties"]["field_status"] == "downgraded"
    assert downgraded["properties"]["engine_type"] == original_properties["type"]
    assert downgraded["properties"]["engine_priority"] == original_properties["priority"]
    assert downgraded["properties"]["field_checked_at"] == "2026-10-13T15:00:00+09:00"
    assert source_path.read_bytes() == original_source


def test_field_worker_cannot_use_citizen_or_admin_map_endpoints() -> None:
    with TestClient(main.app) as client:
        headers = login_as(client, "field_worker")
        facilities = client.get(
            "/api/v1/maps/facilities",
            params={"region": "강남"},
            headers=headers,
        )
        types = client.get(
            "/api/v1/admin/maps/types",
            params={"region": "강남"},
            headers=headers,
        )

    assert facilities.status_code == 403
    assert types.status_code == 403
