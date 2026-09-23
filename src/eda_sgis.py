"""SGIS 단독 EDA."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd
import seaborn as sns

from loaders_srh import load_flow_cell, load_sgis_grid, load_sgis_stats, save_parquet


REGION_COLORS = {"강남": "#D85A30", "춘천": "#1D9E75"}
METRICS = ["senior65_share", "hh_1p_share", "apt_share", "detached_share"]


def configure_matplotlib() -> None:
    plt.rcParams["axes.unicode_minus"] = False
    installed = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in ["AppleGothic", "Noto Sans CJK KR", "NanumGothic", "DejaVu Sans"]:
        if candidate in installed:
            plt.rcParams["font.family"] = [candidate]
            break


def build_sgis_grid() -> gpd.GeoDataFrame:
    stats = load_sgis_stats()
    grid = load_sgis_grid()
    flow = load_flow_cell()
    flow_coordinates = flow[["x", "y"]].drop_duplicates()
    flow_points = gpd.GeoDataFrame(
        flow_coordinates,
        geometry=gpd.points_from_xy(flow_coordinates["x"], flow_coordinates["y"]),
        crs=grid.crs,
    )
    flow_grid = gpd.sjoin(
        flow_points,
        grid[["GRID_CD", "geometry"]],
        how="left",
        predicate="within",
    )
    valid_grid_codes = flow_grid["GRID_CD"].dropna().unique()
    grid = grid[grid["GRID_CD"].isin(valid_grid_codes)].copy()
    print("SGIS flow 기반 격자 수:")
    print(grid.groupby("region")["GRID_CD"].nunique().to_string())
    frame = grid.merge(stats.drop(columns="region"), on="GRID_CD", how="left")
    frame["BASE_YEAR"] = frame["BASE_YEAR"].fillna(2024).astype(int)

    value_columns = [column for column in stats.columns if column not in {"BASE_YEAR", "GRID_CD", "region"}]
    frame[value_columns] = frame[value_columns].apply(pd.to_numeric, errors="coerce").fillna(0)
    frame["total_pop"] = frame.get("to_in_001", 0)
    frame["total_household"] = frame.get("to_ga_001", 0)
    frame["total_housing"] = frame.get("to_ho_001", 0)
    frame["total_business"] = frame.get("to_fa_010", 0)
    frame["total_worker"] = frame.get("to_em_020", 0)
    frame["senior65"] = frame[[f"in_age_{i:03d}" for i in range(14, 22)]].sum(axis=1)
    frame["age_total"] = frame[[f"in_age_{i:03d}" for i in range(1, 22)]].sum(axis=1)
    frame["one_person_household"] = frame.get("ga_sd_005", 0)
    frame["detached_house"] = frame.get("ho_gb_002", 0)
    frame["apartment_house"] = frame.get("ho_gb_003", 0)
    frame["other_housing"] = frame.get("ho_gb_006", 0)
    denominator_pop = frame["total_pop"].replace(0, np.nan)
    denominator_age = frame["age_total"].replace(0, np.nan)
    denominator_household = frame["total_household"].replace(0, np.nan)
    denominator_housing = frame["total_housing"].replace(0, np.nan)
    frame["senior65_share"] = (frame["senior65"] / denominator_age).clip(0, 1)
    frame["hh_1p_share"] = frame["one_person_household"] / denominator_household
    frame["apt_share"] = frame["apartment_house"] / denominator_housing
    frame["detached_share"] = frame["detached_house"] / denominator_housing
    frame["worker_per_pop"] = frame["total_worker"] / denominator_pop
    frame["reliable_flow_per_resident"] = frame["total_pop"] >= 50
    frame["reliable_senior65_share"] = frame["age_total"] >= 200
    frame["reliable_hh_1p_share"] = frame["total_household"] >= 50
    frame["reliable_housing_share"] = frame["total_housing"] >= 50
    frame["reliable"] = frame["reliable_flow_per_resident"]
    frame["housing_density"] = frame["total_housing"] / frame.geometry.area.replace(0, np.nan)
    return frame


def make_tables(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    distribution = (
        frame.groupby("region")
        .agg(
            grid_count=("GRID_CD", "size"),
            total_pop=("total_pop", "sum"),
            pop_median=("total_pop", "median"),
            pop_p25=("total_pop", lambda value: value.quantile(0.25)),
            pop_p75=("total_pop", lambda value: value.quantile(0.75)),
        )
        .reset_index()
        .round(3)
    )
    metric_distribution = []
    for region, group in frame.groupby("region"):
        for metric in METRICS:
            reliable_column = {
                "senior65_share": "reliable_senior65_share",
                "hh_1p_share": "reliable_hh_1p_share",
                "apt_share": "reliable_housing_share",
                "detached_share": "reliable_housing_share",
            }[metric]
            values = group.loc[group[reliable_column], metric].dropna()
            metric_distribution.append(
                {
                    "region": region,
                    "metric": metric,
                    "reliable_n": len(values),
                    "mean": values.mean(),
                    "median": values.median(),
                    "p25": values.quantile(0.25),
                    "p75": values.quantile(0.75),
                }
            )
    zero_population = (
        frame.assign(zero_population=frame["total_pop"] == 0)
        .groupby("region")
        .agg(grid_count=("GRID_CD", "size"), zero_population=("zero_population", "sum"))
        .reset_index()
    )
    zero_population["zero_share"] = zero_population["zero_population"] / zero_population["grid_count"]
    reliable = (
        frame.groupby("region")
        .agg(
            grid_count=("GRID_CD", "size"),
            reliable_flow_count=("reliable_flow_per_resident", "sum"),
            reliable_senior65_count=("reliable_senior65_share", "sum"),
            reliable_hh_1p_count=("reliable_hh_1p_share", "sum"),
        )
        .reset_index()
    )
    reliable["reliable_flow_share"] = reliable["reliable_flow_count"] / reliable["grid_count"]
    reliable["reliable_senior65_share"] = reliable["reliable_senior65_count"] / reliable["grid_count"]
    reliable["reliable_hh_1p_share"] = reliable["reliable_hh_1p_count"] / reliable["grid_count"]
    return {
        "sgis_population_distribution": distribution,
        "sgis_metric_distribution": pd.DataFrame(metric_distribution).round(5),
        "sgis_zero_population": zero_population.round(5),
        "sgis_reliable_share": reliable.round(5),
    }


def _save_population_plot(frame: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    for region, group in frame.groupby("region"):
        zero_count = int(group["total_pop"].eq(0).sum())
        positive = group.loc[group["total_pop"] > 0, "total_pop"]
        bins = np.logspace(np.log10(max(positive.min(), 1)), np.log10(positive.max()), 35)
        sns.histplot(
            positive,
            bins=bins,
            stat="density",
            element="step",
            fill=False,
            color=REGION_COLORS[region],
            label=region,
            ax=ax,
        )
        ax.text(
            0.02,
            0.96 if region == "강남" else 0.88,
            f"{region} 0명 격자: {zero_count}개",
            transform=ax.transAxes,
            color=REGION_COLORS[region],
        )
    ax.set(xscale="log", xlabel="1km 격자 총인구 (1 이상)", ylabel="밀도", title="지역별 1km 격자 총인구 분포")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _save_metric_plot(frame: pd.DataFrame, path: Path) -> None:
    plot_frame = frame.melt(
        id_vars=["region", "reliable_senior65_share", "reliable_hh_1p_share"], value_vars=["senior65_share", "hh_1p_share"],
        var_name="metric", value_name="share"
    )
    plot_frame = plot_frame[
        ((plot_frame["metric"].eq("senior65_share") & plot_frame["reliable_senior65_share"]) |
         (plot_frame["metric"].eq("hh_1p_share") & plot_frame["reliable_hh_1p_share"]))
    ]
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.boxenplot(data=plot_frame, x="metric", y="share", hue="region", palette=REGION_COLORS, ax=ax)
    ax.set(xlabel="지표", ylabel="비율", title="신뢰 격자의 고령·1인가구 비율 비교")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _save_maps(frame: gpd.GeoDataFrame, path: Path) -> None:
    fig, axes = plt.subplots(2, 4, figsize=(22, 11))
    plots = [
        ("total_pop", "총인구", None),
        ("senior65_share", "65세 이상 비중", "reliable_senior65_share"),
        ("hh_1p_share", "1인가구 비율", "reliable_hh_1p_share"),
        ("apt_share", "아파트 비율", "reliable_housing_share"),
    ]
    for row, region in enumerate(["강남", "춘천"]):
        region_frame = frame[frame["region"].eq(region)]
        for column_index, (column, title, reliable_column) in enumerate(plots):
            ax = axes[row, column_index]
            reliability = "reliable_flow_per_resident" if reliable_column is None else reliable_column
            valid = region_frame[region_frame[reliability]]
            region_frame.plot(ax=ax, color="#D0D0D0", linewidth=0)
            if not valid.empty:
                values = valid[column].dropna()
                valid.plot(
                    column=column,
                    ax=ax,
                    cmap="viridis",
                    legend=True,
                    vmin=values.min(),
                    vmax=values.max() if values.max() > values.min() else values.min() + 1,
                    linewidth=0,
                )
            ax.set_title(f"{region} · {title}")
            ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run_sgis(fig_dir: Path) -> tuple[gpd.GeoDataFrame, dict[str, pd.DataFrame]]:
    configure_matplotlib()
    fig_dir.mkdir(parents=True, exist_ok=True)
    frame = build_sgis_grid()
    save_parquet(frame, "sgis_grid")
    tables = make_tables(frame)
    _save_population_plot(frame, fig_dir / "01_sgis_population_distribution.png")
    _save_metric_plot(frame, fig_dir / "02_sgis_senior_household_distribution.png")
    _save_maps(frame, fig_dir / "03_sgis_grid_maps.png")
    return frame, tables