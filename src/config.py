"""프로젝트 공통 경로 · 원천 데이터 포맷 상수."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
EXTERNAL = DATA / "external"

OUTPUTS = ROOT / "outputs"
FIGURES = OUTPUTS / "figures"
TABLES = OUTPUTS / "tables"
SUBMISSIONS = ROOT / "submissions"

# --- SK 유동인구: '|' 구분, UTF-8 BOM ---
SK_DIR = RAW / "sk_flow_pop"
SK_READ_KWARGS = {"sep": "|", "encoding": "utf-8-sig", "dtype": {"BLOCK_CD": "string"}}
SK_KEYS = ["STD_YM", "BLOCK_CD", "X_COORD", "Y_COORD"]
SK_KINDS = ("flow_age_pop", "flow_time_pop", "flow_wkdy_pop")
SK_MONTHS = [f"2025{m:02d}" for m in range(7, 13)]
SK_CRS = "EPSG:5179"  # 50m 격자 추정값 — 검증 필요

# --- 신한카드: 탭 구분, CP949 ---
SHINHAN_DIR = RAW / "shinhan_card"
SHINHAN_READ_KWARGS = {"sep": "\t", "encoding": "cp949"}
SHINHAN_MCT = SHINHAN_DIR / "신한카드_빅콘테스트2026_데이터1.txt"  # 가맹점 기준
SHINHAN_CLN = SHINHAN_DIR / "신한카드_빅콘테스트2026_데이터2_수정.txt"  # 일별×업종×거주지 (2026-09 재배포본)
