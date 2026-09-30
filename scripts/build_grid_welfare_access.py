"""Build 250 m grid-level welfare-resource accessibility features.

The script keeps the original flow grid unchanged.  It combines it with two
standardised, non-sensitive facility lists supplied by the team:

* social_activity_facilities.csv: senior centres, village halls, public
  libraries, public sports facilities and culture facilities
* health_care_facilities.csv: public health centres, health branches and
  health posts

All distances are straight-line distances from the 250 m grid centre in
UTM-K (EPSG:5179).  See docs/welfare_access_integration.md for the input
contract and interpretation limits.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer


ROOT = Path(__file__).resolve().parents[1]
FLOW_GRID_PATH = ROOT / "preprocessed" / "flow_cell.parquet"
EXTERNAL_DIR = ROOT / "external" / "welfare"
SOCIAL_PATH = EXTERNAL_DIR / "social_activity_facilities.csv"
HEALTH_PATH = EXTERNAL_DIR / "health_care_facilities.csv"
OUTPUT_PATH = ROOT / "preprocessed" / "grid_welfare_access.parquet"
DECEMBER_CSV_PATH = ROOT / "outputs" / "tables" / "grid_welfare_access_202512.csv"

REQUIRED_COLUMNS = {"REGION", "FACILITY_NAME", "FACILITY_TYPE", "LATITUDE", "LONGITUDE"}
WGS84_TO_UTMK = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)


def load_facilities(path: Path, label: str) -> pd.DataFrame:
    """Read a standardised facility list and return valid UTM-K points."""
    if not path.exists():
        raise FileNotFoundError(
            f"{label} 파일이 없습니다: {path}\n"
            "입력 형식은 docs/welfare_access_integration.md를 확인하세요."
        )

    frame = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"{label}에 필수 컬럼이 없습니다: {sorted(missing)}")

    result = frame.copy()
    result["LATITUDE"] = pd.to_numeric(result["LATITUDE"], errors="coerce")
    result["LONGITUDE"] = pd.to_numeric(result["LONGITUDE"], errors="coerce")
    result = result[
        result["LATITUDE"].between(33, 39) & result["LONGITUDE"].between(120, 132)
    ].copy()
    if result.empty:
        raise ValueError(f"{label}에 유효한 대한민국 좌표가 없습니다.")

    result["x"], result["y"] = WGS84_TO_UTMK.transform(
        result["LONGITUDE"].to_numpy(), result["LATITUDE"].to_numpy()
    )
    return result.drop_duplicates(["REGION", "x", "y"]).reset_index(drop=True)


def nearest_and_counts(
    grid: pd.DataFrame, facilities: pd.DataFrame, radii_m: tuple[int, ...]
) -> tuple[np.ndarray, dict[int, np.ndarray]]:
    """Calculate nearest distance and facility counts with bounded memory use."""
    grid_xy = grid[["x", "y"]].to_numpy(float)
    facility_xy = facilities[["x", "y"]].to_numpy(float)
    nearest_m = np.empty(len(grid), dtype=float)
    counts = {radius: np.empty(len(grid), dtype=np.int16) for radius in radii_m}

    for start in range(0, len(grid), 3_000):
        end = min(start + 3_000, len(grid))
        distance = np.hypot(
            grid_xy[start:end, None, 0] - facility_xy[None, :, 0],
            grid_xy[start:end, None, 1] - facility_xy[None, :, 1],
        )
        nearest_m[start:end] = distance.min(axis=1)
        for radius in radii_m:
            counts[radius][start:end] = (distance <= radius).sum(axis=1)
    return nearest_m / 1_000, counts


def add_city_access_features(grid: pd.DataFrame, social: pd.DataFrame, health: pd.DataFrame) -> pd.DataFrame:
    """Add accessibility features per city, avoiding cross-city comparisons."""
    pieces: list[pd.DataFrame] = []
    for region, part in grid.groupby("REGION", sort=False):
        social_part = social[social["REGION"].eq(region)]
        health_part = health[health["REGION"].eq(region)]
        if social_part.empty or health_part.empty:
            raise ValueError(f"{region}의 사회활동 또는 건강돌봄 시설이 없습니다.")

        result = part.copy()
        result["nearest_social_km"], social_counts = nearest_and_counts(
            result, social_part, (500, 1_000)
        )
        result["nearest_health_km"], health_counts = nearest_and_counts(
            result, health_part, (1_000, 3_000)
        )
        result["social_within_500m"] = social_counts[500]
        result["social_within_1km"] = social_counts[1_000]
        result["health_within_1km"] = health_counts[1_000]
        result["health_within_3km"] = health_counts[3_000]

        # "Far" means the least-accessible quarter within the same city.
        result["social_far_threshold_km"] = result["nearest_social_km"].quantile(0.75)
        result["health_far_threshold_km"] = result["nearest_health_km"].quantile(0.75)
        social_far = result["nearest_social_km"] >= result["social_far_threshold_km"]
        health_far = result["nearest_health_km"] >= result["health_far_threshold_km"]
        result["resource_access_type"] = np.select(
            [
                ~social_far & ~health_far,
                social_far & ~health_far,
                ~social_far & health_far,
                social_far & health_far,
            ],
            [
                "A. 생활연결 가능형",
                "B. 사회활동 공백형",
                "C. 건강돌봄 공백형",
                "D. 복합생활 공백형",
            ],
            default="분류 제외",
        )
        pieces.append(result)
    return pd.concat(pieces, ignore_index=True)


def main() -> None:
    flow = pd.read_parquet(FLOW_GRID_PATH)
    required_grid_columns = {"cell_id", "REGION", "x", "y"}
    missing = required_grid_columns - set(flow.columns)
    if missing:
        raise ValueError(f"flow_cell.parquet에 필수 컬럼이 없습니다: {sorted(missing)}")

    social = load_facilities(SOCIAL_PATH, "사회활동 자원")
    health = load_facilities(HEALTH_PATH, "건강돌봄 자원")

    # Accessibility is spatially fixed.  Calculate it once per 250 m cell,
    # then join it back to all six monthly flow records.
    cells = flow[["cell_id", "REGION", "x", "y"]].drop_duplicates().reset_index(drop=True)
    access = add_city_access_features(cells, social, health)
    output = flow.merge(access, on=["cell_id", "REGION", "x", "y"], how="left", validate="many_to_one")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DECEMBER_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(OUTPUT_PATH, index=False)

    december = output[output["STD_YM"].astype(str).eq("202512")].copy()
    december.to_csv(DECEMBER_CSV_PATH, index=False, encoding="utf-8-sig")

    print(f"저장 완료: {OUTPUT_PATH.relative_to(ROOT)} ({len(output):,}행)")
    print(f"저장 완료: {DECEMBER_CSV_PATH.relative_to(ROOT)} ({len(december):,}행)")
    print("유형별 격자 수:")
    print(december.groupby(["REGION", "resource_access_type"]).size())


if __name__ == "__main__":
    main()
