"""SRH EDA 단일 실행 진입점."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import config as C
from eda_sgis import run_sgis
from eda_srh import run_card2, run_combined


def _slug(value: str) -> str:
    return "_".join(value.lower().replace(" ", "_").split())


TABLE_NUMBERS = {
    "sgis_population_distribution": 1,
    "sgis_metric_distribution": 2,
    "sgis_zero_population": 3,
    "sgis_reliable_share": 4,
    "srh_resident_cell_summary": 5,
    "srh_resident_definition_sensitivity": 6,
    "srh_candidate_cells": 7,
    "srh_chuncheon_housing_sensitivity": 8,
    "srh_candidate_validity": 9,
    "srh_threshold_sensitivity": 10,
    "srh_cluster_profiles": 11,
    "srh_flow_sgis_comparison": 12,
    "srh_card2_home_share": 13,
    "srh_card2_age_industry_share": 14,
    "srh_card2_solo_month": 15,
    "srh_card2_age_sample": 16,
    "srh_card2_entropy": 17,
    "srh_card2_weekend_weekday": 18,
}


def _write_tables(tables: dict[str, pd.DataFrame], manifest: list[dict]) -> None:
    C.TABLES.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        index = TABLE_NUMBERS[name]
        path = C.TABLES / f"srh_{index:02d}_{_slug(name.removeprefix('srh_'))}.csv"
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        manifest.append({"name": name, "file": path.name, "rows": len(frame), "columns": list(frame.columns)})
        print(f"[{index:02d}] {path.name}: {frame.shape}")


def main() -> None:
    fig_dir = C.OUTPUTS / "fig_srh"
    manifest: list[dict] = []

    sgis, sgis_tables = run_sgis(fig_dir)
    _write_tables(sgis_tables, manifest)

    combined_tables, match_rate = run_combined(sgis, fig_dir)
    _write_tables(combined_tables, manifest)

    card_tables = run_card2(fig_dir)
    _write_tables(card_tables, manifest)

    manifest_path = C.OUTPUTS / "srh_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
    resident = combined_tables["srh_resident_cell_summary"]
    candidates = combined_tables["srh_candidate_cells"]
    outside = card_tables["srh_card2_home_share"]
    outside = outside[outside["home_status"].eq("외지")]
    outside_month = outside.groupby(["region", "month"], as_index=False)["share"].sum()
    print(f"SGIS 셀 매칭률: {match_rate:.2%}")
    print("지역별 1km 격자 수:")
    print(sgis.groupby("region").size().to_string())
    print(f"senior65_share 최대값: {sgis['senior65_share'].max():.6f}")
    print("거주 셀 요약:")
    print(resident.to_string(index=False))
    print("거주 셀 기준값 민감도:")
    print(combined_tables["srh_resident_definition_sensitivity"].to_string(index=False))
    print("지역별 후보 수:")
    print(candidates.groupby("region").size().to_string())
    print("춘천 외지인 소비 비중 월별:")
    print(outside_month[outside_month.region.eq("춘천")].to_string(index=False))
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()