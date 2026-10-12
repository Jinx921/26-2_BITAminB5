from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


def _checked_at(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def latest_checks_by_cell(
    checks: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    latest_order: dict[str, tuple[datetime, int]] = {}
    for check in checks:
        cell_id = check["cell_id"]
        order = (_checked_at(check["checked_at"]), int(check["id"]))
        if cell_id not in latest_order or order > latest_order[cell_id]:
            latest[cell_id] = check
            latest_order[cell_id] = order
    return latest


def apply_field_overrides(
    geojson: dict[str, Any],
    latest_checks: dict[str, dict[str, Any]],
    *,
    show_excluded: bool,
) -> dict[str, Any]:
    result = deepcopy(geojson)
    features = []
    for feature in result.get("features", []):
        properties = feature.get("properties") or {}
        check = latest_checks.get(properties.get("cell_id"))
        if check is not None:
            answers = check["checklist"]
            if answers.get("has_residents") == "no":
                properties["engine_type"] = properties.get("type")
                properties["engine_priority"] = properties.get("priority")
                properties["field_status"] = "excluded"
                properties["field_checked_at"] = check["checked_at"]
                if not show_excluded:
                    continue
            elif answers.get("support_needed") == "not_needed":
                properties["engine_type"] = properties.get("type")
                properties["engine_priority"] = properties.get("priority")
                properties["type"] = "관찰형"
                properties["priority"] = 4
                properties["field_status"] = "downgraded"
                properties["field_checked_at"] = check["checked_at"]
            feature["properties"] = properties
        features.append(feature)
    result["features"] = features
    return result
