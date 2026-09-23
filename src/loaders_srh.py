"""SRH 분석용 SGIS·카드2·기존 parquet 로더."""
from __future__ import annotations

import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd

import config as C
import loaders


SGIS_CODES = ("다사", "라사", "라아")
REGION_BY_CODE = {"다사": "강남", "라사": "춘천", "라아": "춘천"}
SGIS_CATEGORIES = {
    "인구": "인구",
    "가구": "가구",
    "주택": "주택",
    "사업체": "사업체",
    "종사자": "종사자",
}
SGIS_VALUE_COLUMNS = {
    "기준연도": "BASE_YEAR",
    "격자코드": "GRID_CD",
    "통계항목": "item_identifier",
    "통계값": "item_value",
}


def _nfc(value: object) -> str:
    return unicodedata.normalize("NFC", str(value))


def _data_root() -> Path:
    return C.ROOT / "data"


def _find_file(predicate) -> Path:
    matches = [path for path in _data_root().rglob("*") if path.is_file() and predicate(path)]
    if not matches:
        raise FileNotFoundError("분석 대상 데이터 파일을 찾지 못했습니다")
    return sorted(matches, key=lambda path: str(path))[0]


def _sgis_root() -> Path:
    return next(
        path for path in _data_root().iterdir() if path.is_dir() and "SGIS" in _nfc(path.name)
    )


def load_flow_cell() -> pd.DataFrame:
    """기존 250m 집계 parquet을 로드한다."""
    return pd.read_parquet(C.ROOT / "preprocessed" / "flow_cell.parquet")


def load_card_clean() -> pd.DataFrame:
    """기존 데이터1 정제 parquet을 로드한다."""
    return pd.read_parquet(C.ROOT / "preprocessed" / "card_clean.parquet")


def load_card2() -> pd.DataFrame:
    """재배포된 카드 데이터2를 CP949 탭 구분으로 읽는다."""
    path = _find_file(lambda p: "데이터2" in _nfc(p.name) and p.suffix.lower() == ".txt")
    frame = pd.read_csv(path, sep="\t", encoding="cp949")
    frame["TA_YMD"] = frame["TA_YMD"].astype(str).str.replace(".0", "", regex=False).str.zfill(8)
    frame["date"] = pd.to_datetime(frame["TA_YMD"], format="%Y%m%d")
    frame["month"] = frame["date"].dt.to_period("M").astype(str)
    frame["region"] = frame["MCT_SGG_CD"].map({"서울 강남구": "강남", "강원 춘천시": "춘천"})
    return frame[frame["region"].notna()].copy()


def _sgis_csv(category: str, code: str) -> Path:
    normalized_name = f"2024년_{category}_{code}_1K.csv"
    return _find_file(
        lambda p: p.suffix.lower() == ".csv" and _nfc(p.name) == normalized_name
    )


def load_sgis_stats(codes: tuple[str, ...] = SGIS_CODES) -> pd.DataFrame:
    """요청한 1km 격자 SGIS 통계를 long-to-wide로 결합한다."""
    frames = []
    for category in SGIS_CATEGORIES:
        for code in codes:
            path = _sgis_csv(category, code)
            frame = pd.read_csv(path, encoding="cp949")
            frame = frame.rename(columns=SGIS_VALUE_COLUMNS)
            frame = frame[["BASE_YEAR", "GRID_CD", "item_identifier", "item_value"]]
            frame["region"] = REGION_BY_CODE[code]
            frame["source_category"] = category
            frames.append(frame)

    long = pd.concat(frames, ignore_index=True)
    wide = (
        long.pivot_table(
            index=["BASE_YEAR", "GRID_CD", "region"],
            columns="item_identifier",
            values="item_value",
            aggfunc="first",
        )
        .reset_index()
    )
    wide.columns.name = None
    return wide


def _sgis_shp(code: str) -> Path:
    expected = f"grid_{code}_1K.shp"
    return _find_file(lambda p: p.suffix.lower() == ".shp" and _nfc(p.name) == expected)


def load_sgis_grid(codes: tuple[str, ...] = SGIS_CODES) -> gpd.GeoDataFrame:
    """요청한 1km 격자 경계를 EPSG:5179로 반환한다."""
    frames = []
    for code in codes:
        frame = gpd.read_file(_sgis_shp(code))
        frame["region"] = REGION_BY_CODE[code]
        frames.append(frame[["GRID_CD", "region", "geometry"]])
    grid = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=frames[0].crs)
    if grid.crs is None:
        grid = grid.set_crs(C.SK_CRS)
    return grid.to_crs(C.SK_CRS)


def save_parquet(frame: pd.DataFrame, name: str) -> Path:
    """SRH 중간 산출물을 preprocessed에 저장한다."""
    path = C.ROOT / "preprocessed" / f"{name}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path