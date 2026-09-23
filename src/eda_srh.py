"""공통데이터 보완, SGIS 결합, 카드 데이터2 EDA."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from shapely.geometry import Point

from config_srh import (
    CHUNCHEON_HOUSING_SENSITIVITY,
    MIN_CLUSTER_CELLS,
    REGION_HOUSING_THRESHOLDS,
    REGION_NIGHT_SHARE_THRESHOLDS,
)
from eda_sgis import REGION_COLORS, configure_matplotlib
from loaders_srh import load_card2, load_card_clean, load_flow_cell, save_parquet


SOLO_INDUSTRIES = {
    "편의점", "패스트푸드", "커피전문점", "할인점/슈퍼마켓/양판점", "쇼핑몰",
    "결제대행(PG)", "통신요금(이동,시내전화)", "택시", "주차장",
}
SOCIAL_INDUSTRIES = {
    "한식", "중식", "일식", "양식", "기타요식", "주류판매", "노래방", "게임방/오락실",
    "스포츠시설", "헬스장", "실내/실외골프장", "싸우나/목욕탕", "영화/공연",
    "종합레저타운/놀이동산", "미용실", "미용서비스", "서점", "문화용품",
}
MEDICAL_INDUSTRIES = {
    "일반병원", "종합병원", "치과병원", "한의원", "약국", "보건소", "기타의료",
}


def _region_from_flow(frame: pd.DataFrame) -> pd.Series:
    return frame["sgg_nm"].map({"강남구": "강남", "춘천시": "춘천"})


def map_flow_cells(grid: gpd.GeoDataFrame) -> tuple[pd.DataFrame, float]:
    flow = load_flow_cell().copy()
    flow["region"] = _region_from_flow(flow)
    points = gpd.GeoDataFrame(
        flow,
        geometry=[Point(x, y) for x, y in zip(flow["x"], flow["y"])],
        crs=grid.crs,
    )
    grid_for_join = grid[["GRID_CD", "geometry"]]
    joined = gpd.sjoin(points, grid_for_join, how="left", predicate="within")
    mapping = joined[["STD_YM", "cell_id", "region", "GRID_CD"]].drop_duplicates()
    match_rate = mapping["GRID_CD"].notna().mean()
    save_parquet(mapping, "cell_grid_map")
    return mapping, float(match_rate)


def _grid_flow_summary(flow: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    merged = flow.merge(mapping, on=["STD_YM", "cell_id", "region"], how="left")
    monthly = (
        merged.dropna(subset=["GRID_CD"])
        .groupby(["GRID_CD", "region", "STD_YM"], as_index=False)
        .agg(
            flow=("tot_time", "sum"),
            senior_flow=("senior", "sum"),
            resident_cells=("cell_id", "nunique"),
        )
    )
    monthly["flow_senior_share"] = monthly["senior_flow"] / monthly["flow"].replace(0, np.nan)
    summary = (
        monthly.groupby(["GRID_CD", "region"], as_index=False)
        .agg(
            flow_mean=("flow", "mean"),
            flow_months=("STD_YM", "nunique"),
            flow_senior_share=("flow_senior_share", "mean"),
            resident_cells=("resident_cells", "max"),
        )
    )
    return summary


def _cell_features(flow: pd.DataFrame) -> pd.DataFrame:
    profile_columns = [f"p_TMST_{hour:02d}" for hour in range(24)]
    day_columns = [f"p_TMST_{hour:02d}" for hour in range(10, 17)]
    features = (
        flow.assign(day_share=flow[day_columns].sum(axis=1))
        .groupby(["region", "cell_id"], as_index=False)[profile_columns + ["day_hold", "day_share", "senior_ratio", "night_share"]]
        .mean()
    )
    for region, index in features.groupby("region").groups.items():
        values = features.loc[index, profile_columns].fillna(0)
        scaled = StandardScaler().fit_transform(values)
        k = min(8, len(index))
        labels = KMeans(n_clusters=k, random_state=42, n_init=20).fit_predict(scaled)
        features.loc[index, "cluster"] = [f"{region}_{label + 1}" for label in labels]
    features["cluster"] = features["cluster"].astype(str)
    features["cluster_raw"] = features["cluster"]
    cluster_sizes = features.groupby(["region", "cluster"]).size()
    small = cluster_sizes[cluster_sizes < MIN_CLUSTER_CELLS]
    if not small.empty:
        print("셀 수 10 미만 군집 제외:")
        print(small.to_string())
        small_keys = set(small.index)
        features.loc[
            features.set_index(["region", "cluster"]).index.isin(small_keys),
            "cluster",
        ] = np.nan
    return features


def _robust_deviation(flow: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    day_columns = [f"p_TMST_{hour:02d}" for hour in range(10, 17)]
    work = flow.copy()
    work["day_share"] = work[day_columns].sum(axis=1).clip(0, 1)
    work = work.merge(features[["region", "cell_id", "cluster"]], on=["region", "cell_id"], how="left")
    group_columns = ["region", "cluster", "STD_YM"]
    old_grouped = work.groupby(group_columns, dropna=True)["day_hold"]
    old_mad = old_grouped.transform(lambda value: np.nanmedian(np.abs(value - np.nanmedian(value))))
    old_scale = (1.4826 * old_mad).replace(0, np.nan)
    old_z = (work["day_hold"] - old_grouped.transform("median")) / old_scale
    old_group_mad = work.assign(_mad=old_mad).drop_duplicates(group_columns)
    print(
        "day_hold 진단: "
        f"MAD=0 그룹 {int(old_group_mad['_mad'].eq(0).sum())}, "
        f"z=0 셀 비율 {float(old_z.eq(0).mean()):.2%}, "
        f"NaN/inf 비율 {float((~np.isfinite(work['day_hold'])).mean()):.2%}, "
        f"야간합계 0 비율 {float(work['night'].eq(0).mean()):.2%}"
    )
    grouped = work.groupby(group_columns, dropna=True)["day_share"]
    median = grouped.transform("median")
    mad = grouped.transform(lambda value: np.nanmedian(np.abs(value - np.nanmedian(value))))
    mad_zero = mad.eq(0)
    scale = (1.4826 * mad).where(~mad_zero)
    work["dev_day_share"] = (work["day_share"] - median) / scale
    work["pct_day_share"] = grouped.rank(pct=True, method="average").where(~mad_zero)
    work["robust_z"] = work["dev_day_share"]
    work["percentile"] = work["pct_day_share"]
    valid_z = work["dev_day_share"].notna() & np.isfinite(work["dev_day_share"])
    group_mad = work.assign(_mad=mad).drop_duplicates(group_columns)
    print(
        "day_share 진단: "
        f"MAD=0 그룹 {int(group_mad['_mad'].eq(0).sum())}, "
        f"z=0 셀 비율 {float(work.loc[valid_z, 'dev_day_share'].eq(0).mean()):.2%}, "
        f"제외 셀 수 {int((~valid_z).sum())}"
    )
    return work


def _candidate_analysis(
    flow: pd.DataFrame, sgis: pd.DataFrame, features: pd.DataFrame
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, dict[str, float]]:
    grid_lookup = sgis[["GRID_CD", "region", "total_pop", "total_housing", "housing_density", "senior65_share", "hh_1p_share", "geometry"]]
    mapping = pd.read_parquet(Path("preprocessed") / "cell_grid_map.parquet")
    cell_grid = flow.merge(mapping, on=["STD_YM", "cell_id", "region"], how="left")
    cell_grid = cell_grid.merge(grid_lookup.drop(columns="geometry"), on=["GRID_CD", "region"], how="left")
    features = features.merge(
        cell_grid.groupby(["region", "cell_id"], as_index=False)["GRID_CD"].first(),
        on=["region", "cell_id"], how="left",
    )
    work = _robust_deviation(cell_grid, features)
    work["night_resident"] = work["night_share"] >= work["region"].map(REGION_NIGHT_SHARE_THRESHOLDS)
    work["housing_threshold"] = work["region"].map(REGION_HOUSING_THRESHOLDS)
    work["housing_resident"] = work["total_housing"] >= work["housing_threshold"]
    work["resident_cell"] = work["night_resident"] & work["housing_resident"]
    senior_threshold_all = work.groupby("region")["senior_ratio"].quantile(0.75).to_dict()
    senior_threshold_resident = (
        work[work["resident_cell"]]
        .groupby("region")["senior_ratio"]
        .quantile(0.75)
        .to_dict()
    )
    print(f"고령비중 상위 25% 임계값(전체): {senior_threshold_all}")
    print(f"고령비중 상위 25% 임계값(거주 셀): {senior_threshold_resident}")
    work["senior_top25"] = work["senior_ratio"] >= work["region"].map(senior_threshold_resident)
    work["day_share_bottom25"] = work["dev_day_share"] < 0

    def candidate_cells(resident_column: str = "resident_cell") -> pd.DataFrame:
        resident_thresholds = (
            work[work[resident_column]]
            .groupby("region")["senior_ratio"]
            .quantile(0.75)
            .to_dict()
        )
        senior_top25 = work["senior_ratio"] >= work["region"].map(resident_thresholds)
        cell_counts = (
            work[work[resident_column] & senior_top25 & work["day_share_bottom25"]]
            .groupby(["region", "cell_id"], as_index=False)
            .agg(persistent_months=("STD_YM", "nunique"), GRID_CD=("GRID_CD", "first"))
        )
        return cell_counts[cell_counts["persistent_months"] >= 4].copy()

    candidates = candidate_cells()
    candidates = candidates.merge(features, on=["region", "cell_id", "GRID_CD"], how="left")
    candidate_keys = candidates[["region", "cell_id"]].drop_duplicates().assign(candidate=True)
    work = work.merge(candidate_keys, on=["region", "cell_id"], how="left")
    work["candidate"] = work["candidate"].fillna(False)
    resident_cells = (
        work[work["resident_cell"]]
        .groupby(["region", "cell_id"], as_index=False)
        .agg(GRID_CD=("GRID_CD", "first"), candidate=("candidate", "any"))
    )
    resident_cells = resident_cells.merge(
        sgis[["GRID_CD", "region", "senior65_share", "hh_1p_share"]].drop_duplicates(),
        on=["GRID_CD", "region"],
        how="left",
    )
    validity_rows = []
    for (region, candidate), group in resident_cells.groupby(["region", "candidate"]):
        for metric in ["senior65_share", "hh_1p_share"]:
            values = group[metric].dropna()
            validity_rows.append({
                "region": region,
                "cell_group": "후보" if candidate else "비후보 거주 셀",
                "metric": metric,
                "n": len(values),
                "median": values.median(),
                "p25": values.quantile(0.25),
                "p75": values.quantile(0.75),
            })
    threshold_rows = []
    for threshold in [1, 5, 10, 50]:
        eligible = work[work["tot_time"] >= threshold]
        eligible_cells = eligible.groupby(["region", "cell_id"]).size().reset_index(name="n")
        eligible_ids = eligible_cells[["region", "cell_id"]]
        candidate_count = candidates.merge(eligible_ids, on=["region", "cell_id"]).groupby("region").size()
        analysis_count = eligible_ids.groupby("region").size()
        for region in ["강남", "춘천"]:
            threshold_rows.append({
                "region": region,
                "monthly_flow_threshold": threshold,
                "analysis_cells": int(analysis_count.get(region, 0)),
                "candidate_cells": int(candidate_count.get(region, 0)),
            })
    comparison = sgis.merge(
        _grid_flow_summary(flow, pd.read_parquet(Path("preprocessed") / "cell_grid_map.parquet")),
        on=["GRID_CD", "region"], how="left",
    )
    comparison["flow_per_resident"] = comparison["flow_mean"] / comparison["total_pop"].replace(0, np.nan)
    comparison["flow_resident_senior_gap"] = comparison["flow_senior_share"] - comparison["senior65_share"]
    resident_rows = []
    resident_conditions = {
        "night_only": "night_resident",
        "housing_only": "housing_resident",
        "night_and_housing": "resident_cell",
    }
    for condition, resident_column in resident_conditions.items():
        residents = work.loc[work[resident_column]].drop_duplicates(["region", "cell_id"])
        threshold_candidates = candidate_cells(resident_column)
        for region in ["강남", "춘천"]:
            total_cells = int(work.loc[work["region"].eq(region), "cell_id"].nunique())
            region_residents = residents[residents["region"].eq(region)]
            resident_rows.append({
                "region": region,
                "resident_definition": condition,
                "night_share_threshold": REGION_NIGHT_SHARE_THRESHOLDS[region],
                "housing_threshold": REGION_HOUSING_THRESHOLDS[region],
                "resident_cells": int(region_residents["cell_id"].nunique()),
                "all_cells": total_cells,
                "resident_share": region_residents["cell_id"].nunique() / total_cells,
                "candidate_cells": int(threshold_candidates.loc[threshold_candidates["region"].eq(region)].shape[0]),
            })
    housing_rows = []
    for chuncheon_threshold in CHUNCHEON_HOUSING_SENSITIVITY:
        threshold_by_region = {"강남": REGION_HOUSING_THRESHOLDS["강남"], "춘천": chuncheon_threshold}
        housing_mask = work["total_housing"] >= work["region"].map(threshold_by_region)
        resident_mask = work["night_resident"] & housing_mask
        resident_thresholds = (
            work[resident_mask]
            .groupby("region")["senior_ratio"]
            .quantile(0.75)
            .to_dict()
        )
        custom_senior_top25 = work["senior_ratio"] >= work["region"].map(resident_thresholds)
        custom_candidates = (
            work[resident_mask & custom_senior_top25 & work["day_share_bottom25"]]
            .groupby(["region", "cell_id"], as_index=False)
            .agg(persistent_months=("STD_YM", "nunique"))
        )
        custom_candidates = custom_candidates[custom_candidates["persistent_months"] >= 4]
        resident_cell_level = (
            work.assign(_resident=resident_mask)
            .groupby(["region", "cell_id"], as_index=False)
            .agg(resident=("_resident", "any"))
        )
        for region in ["강남", "춘천"]:
            region_cells = resident_cell_level[resident_cell_level["region"].eq(region)]
            region_resident = region_cells[region_cells["resident"]]
            housing_rows.append({
                "region": region,
                "chuncheon_housing_threshold": chuncheon_threshold,
                "housing_threshold_used": threshold_by_region[region],
                "resident_cells": int(region_resident["cell_id"].nunique()),
                "all_cells": int(region_cells["cell_id"].nunique()),
                "candidate_cells": int(custom_candidates.loc[custom_candidates["region"].eq(region)].shape[0]),
            })
    cluster_profiles = features.groupby(["region", "cluster"], as_index=False).mean(numeric_only=True)
    cluster_counts = features.groupby(["region", "cluster"], as_index=False).size().rename(columns={"size": "cell_count"})
    cluster_profiles = cluster_profiles.merge(cluster_counts, on=["region", "cluster"], how="left")
    tables = {
        "srh_resident_cell_summary": pd.DataFrame([{
            "region": region,
            "resident_cells": int(work.loc[work.region.eq(region), "resident_cell"].groupby(work.loc[work.region.eq(region), "cell_id"]).any().sum()),
            "all_cells": int(work.loc[work.region.eq(region), "cell_id"].nunique()),
        } for region in ["강남", "춘천"]]),
        "srh_resident_definition_sensitivity": pd.DataFrame(resident_rows),
        "srh_chuncheon_housing_sensitivity": pd.DataFrame(housing_rows),
        "srh_candidate_validity": pd.DataFrame(validity_rows).round(5),
        "srh_candidate_cells": candidates.drop(columns="geometry", errors="ignore"),
        "srh_threshold_sensitivity": pd.DataFrame(threshold_rows),
        "srh_cluster_profiles": cluster_profiles,
        "srh_flow_sgis_comparison": comparison.drop(columns="geometry", errors="ignore"),
    }
    return tables, work, senior_threshold_resident


def _save_cluster_plot(features: pd.DataFrame, path: Path) -> None:
    profile_columns = [f"p_TMST_{hour:02d}" for hour in range(24)]
    profile = features.groupby(["region", "cluster"])[profile_columns].mean().reset_index()
    counts = features.groupby(["region", "cluster_raw"]).size().reset_index(name="cell_count")
    excluded = set(features.loc[features["cluster"].isna(), "cluster_raw"])
    counts["excluded"] = counts["cluster_raw"].isin(excluded)
    fig, axes = plt.subplots(1, 3, figsize=(19, 6), gridspec_kw={"width_ratios": [1, 1, 1.2]})
    for ax, region in zip(axes[:2], ["강남", "춘천"]):
        for _, row in profile[profile.region.eq(region)].iterrows():
            ax.plot(range(24), row[profile_columns], label=row["cluster"])
        ax.set_title(region)
        ax.set_xlabel("시각")
        ax.set_ylabel("시간대 비중")
        ax.legend(fontsize=7)
    sns.barplot(
        data=counts,
        x="cell_count",
        y="cluster_raw",
        hue="excluded",
        palette={False: "#777777", True: "#C03750"},
        ax=axes[2],
    )
    axes[2].set(title="군집별 셀 수", xlabel="셀 수", ylabel="군집")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _save_candidate_scatter(work: pd.DataFrame, senior_thresholds: dict[str, float], path: Path) -> None:
    sample = work.drop_duplicates(["region", "cell_id"])
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, region in zip(axes, ["강남", "춘천"]):
        region_data = sample[sample["region"].eq(region)]
        threshold = senior_thresholds[region]
        sns.scatterplot(
            data=region_data,
            x="senior_ratio",
            y="dev_day_share",
            hue="candidate",
            palette={False: "#B8B8B8", True: "#C03750"},
            alpha=0.65,
            ax=ax,
        )
        ax.axvline(
            threshold, color="#555555", linestyle="--", linewidth=1,
            label=f"고령 상위 25% 임계값(거주 셀 기준) {threshold:.4f}",
        )
        ax.axhline(0, color="#555555", linewidth=1)
        ax.set_title(f"{region} (전체 {len(region_data)}개 / 후보 {int(region_data['candidate'].sum())}개)")
        ax.set_xlabel("유동인구 60+ 비중")
        ax.set_ylabel("주간활동 day_share robust z")
        ax.legend(title="후보")
        ax.set_ylim(-5, 5)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _save_candidate_cell_map(work: pd.DataFrame, path: Path) -> None:
    cells = (
        work.groupby(["region", "cell_id"], as_index=False)
        .agg(x=("x", "first"), y=("y", "first"), resident_cell=("resident_cell", "any"), candidate=("candidate", "any"))
    )
    points = gpd.GeoDataFrame(cells, geometry=gpd.points_from_xy(cells["x"], cells["y"]), crs="EPSG:5179")
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, region in zip(axes, ["강남", "춘천"]):
        subset = points[points["region"].eq(region)]
        subset[~subset["resident_cell"]].plot(ax=ax, color="#666666", markersize=2, label="비거주")
        subset[subset["resident_cell"]].plot(ax=ax, color="#D9D9D9", markersize=3, label="거주")
        subset[subset["candidate"]].plot(ax=ax, color="#C03750", markersize=5, label="후보")
        ax.set_title(f"{region} (거주 {int(subset['resident_cell'].sum())} / 전체 {len(subset)})")
        ax.set_axis_off()
        ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _save_sensitivity_plot(table: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=table, x="monthly_flow_threshold", y="candidate_cells", hue="region", palette=REGION_COLORS, ax=ax)
    ax.set(xlabel="월총유동 임계값", ylabel="후보 셀 수", title="후보 셀 임계값 민감도")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run_combined(sgis: gpd.GeoDataFrame, fig_dir: Path) -> tuple[dict[str, pd.DataFrame], float]:
    configure_matplotlib()
    flow = load_flow_cell().copy()
    flow["region"] = _region_from_flow(flow)
    mapping, match_rate = map_flow_cells(sgis)
    flow_summary = _grid_flow_summary(flow, mapping)
    features = _cell_features(flow)
    tables, work, senior_thresholds = _candidate_analysis(flow, sgis, features)
    fig_dir.mkdir(parents=True, exist_ok=True)
    _save_cluster_plot(features, fig_dir / "04_srh_cluster_profiles.png")
    _save_candidate_scatter(work, senior_thresholds, fig_dir / "05_srh_senior_percentile.png")
    _save_candidate_cell_map(work, fig_dir / "06_srh_candidate_cells.png")
    _save_sensitivity_plot(tables["srh_threshold_sensitivity"], fig_dir / "07_srh_threshold_sensitivity.png")
    return tables, match_rate


def _classify_home(frame: pd.DataFrame) -> pd.DataFrame:
    expected = frame["region"].map({"강남": "서울", "춘천": "강원"})
    frame["home_status"] = np.select(
        [frame["CLN_SGG_CD"].eq(expected), frame["CLN_SGG_CD"].eq("정보없음")],
        ["거주", "미상"],
        default="외지",
    )
    frame["age_clean"] = frame["AGE_CCD"].astype(str).str.replace(" ", "", regex=False)
    frame["industry_group"] = np.select(
        [frame["MCT_RY_CD"].isin(SOLO_INDUSTRIES), frame["MCT_RY_CD"].isin(SOCIAL_INDUSTRIES), frame["MCT_RY_CD"].isin(MEDICAL_INDUSTRIES)],
        ["SOLO", "SOCIAL", "MEDICAL"], default="OTHER",
    )
    return frame


def _entropy(values: pd.Series) -> float:
    share = values / values.sum()
    share = share[share > 0]
    return float(-(share * np.log(share)).sum())


def run_card2(fig_dir: Path) -> dict[str, pd.DataFrame]:
    configure_matplotlib()
    data = _classify_home(load_card2())
    save_parquet(data, "card2_clean")
    resident = data[data["home_status"].eq("거주")].copy()
    total = data.groupby(["region", "month", "home_status"], as_index=False)["USE_CNT"].sum()
    total["share"] = total["USE_CNT"] / total.groupby(["region", "month"])["USE_CNT"].transform("sum")
    age_group = resident.groupby(["region", "age_clean", "industry_group"], as_index=False)["USE_CNT"].sum()
    age_group["share"] = age_group["USE_CNT"] / age_group.groupby(["region", "age_clean"])["USE_CNT"].transform("sum")
    age_size = resident.groupby(["region", "age_clean"], as_index=False)["USE_CNT"].sum()
    age_size["share"] = age_size["USE_CNT"] / age_size.groupby("region")["USE_CNT"].transform("sum")
    solo_month = resident.assign(is_solo=resident["industry_group"].eq("SOLO")).groupby(["region", "month"], as_index=False).apply(lambda group: pd.Series({"solo_share": group.loc[group.is_solo, "USE_CNT"].sum() / group.USE_CNT.sum()}), include_groups=False)
    entropy_rows = []
    for (region, age), group in resident.groupby(["region", "age_clean"]):
        size = age_size[(age_size.region == region) & (age_size.age_clean == age)]["share"].iloc[0]
        if size >= 0.01:
            for month, month_group in group.groupby("month"):
                entropy_rows.append({"region": region, "age": age, "month": month, "entropy": _entropy(month_group.groupby("MCT_RY_CD")["USE_CNT"].sum())})
    daily = resident.groupby(["region", "date"], as_index=False)["USE_CNT"].sum()
    daily["day_type"] = np.where(daily["date"].dt.dayofweek >= 5, "주말", "평일")
    weekend = daily.groupby(["region", "day_type"], as_index=False)["USE_CNT"].mean().pivot(index="region", columns="day_type", values="USE_CNT").reset_index()
    weekend["주말_평일_비율"] = weekend["주말"] / weekend["평일"]
    tables = {
        "srh_card2_home_share": total,
        "srh_card2_age_industry_share": age_group,
        "srh_card2_solo_month": solo_month,
        "srh_card2_age_sample": age_size,
        "srh_card2_entropy": pd.DataFrame(entropy_rows),
        "srh_card2_weekend_weekday": weekend,
    }
    plot_data = age_group[age_group["industry_group"].isin(["SOLO", "SOCIAL"])]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, industry in zip(axes, ["SOLO", "SOCIAL"]):
        sns.barplot(
            data=plot_data[plot_data["industry_group"].eq(industry)],
            x="age_clean", y="share", hue="region", palette=REGION_COLORS, ax=ax,
        )
        ax.set_title(f"거주민 {industry} 업종 비중")
        ax.set_xlabel("연령대")
        ax.set_ylabel("비중")
        ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(fig_dir / "08_srh_card2_age_industry.png", dpi=160)
    plt.close(fig)
    return tables