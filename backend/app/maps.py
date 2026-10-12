from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from starlette.concurrency import run_in_threadpool

from backend.app.auth import require_roles
from backend.app.errors import ApiError
from backend.app.field_overrides import apply_field_overrides, latest_checks_by_cell

router = APIRouter(tags=["maps"])
ENGINE_OUT = Path(__file__).resolve().parents[2] / "engine" / "out"
FACILITY_PROPERTIES = frozenset({"fac_id", "name", "addr", "kind", "group"})
PLACEMENT_RADII = (1000, 3000)
PLACEMENT_SITES = (3,)


def _read_geojson(filename: str) -> dict[str, Any]:
    path = ENGINE_OUT / filename
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApiError(
            500,
            "map_data_unavailable",
            "Map data is unavailable",
        ) from exc


def _citizen_facilities(geojson: dict[str, Any]) -> dict[str, Any]:
    features = []
    for feature in geojson.get("features", []):
        source_properties = feature.get("properties") or {}
        features.append(
            {
                "type": "Feature",
                "geometry": feature.get("geometry"),
                "properties": {
                    key: value
                    for key, value in source_properties.items()
                    if key in FACILITY_PROPERTIES
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@router.get("/api/v1/maps/facilities")
async def citizen_facilities(
    region: Literal["강남", "춘천"],
    _user: dict = Depends(require_roles("citizen", "admin")),
) -> dict[str, Any]:
    geojson = await run_in_threadpool(
        _read_geojson, f"facilities_{region}.geojson"
    )
    return _citizen_facilities(geojson)


@router.get("/api/v1/admin/maps/types")
async def admin_types(
    request: Request,
    region: Literal["강남", "춘천"],
    show_excluded: bool = False,
    _user: dict = Depends(require_roles("admin")),
) -> dict[str, Any]:
    geojson = await run_in_threadpool(_read_geojson, f"types_{region}.geojson")
    checks = await run_in_threadpool(
        request.app.state.database.list_all_field_checks
    )
    latest = latest_checks_by_cell(checks)
    return apply_field_overrides(
        geojson, latest, show_excluded=show_excluded
    )


@router.get("/api/v1/admin/maps/candidates")
async def admin_candidates(
    region: Literal["강남", "춘천"],
    _user: dict = Depends(require_roles("admin")),
) -> dict[str, Any]:
    return await run_in_threadpool(
        _read_geojson, f"candidates_{region}.geojson"
    )


@router.get("/api/v1/admin/maps/placements")
async def admin_placements(
    region: Literal["강남", "춘천"],
    radius_m: int = Query(default=1000),
    sites: int = Query(default=3),
    _user: dict = Depends(require_roles("admin")),
) -> dict[str, Any]:
    if radius_m not in PLACEMENT_RADII or sites not in PLACEMENT_SITES:
        raise ApiError(422, "validation_error", "Unsupported placement selection")
    return await run_in_threadpool(
        _read_geojson,
        f"sim_{region}_k{sites}_r{radius_m}.geojson",
    )
