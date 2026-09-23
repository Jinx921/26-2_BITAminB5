"""원천 데이터 로더. 인코딩·구분자 차이를 여기서만 처리한다."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

import config as C


def load_sk(kind: str, months: list[str] | None = None, **kwargs) -> pd.DataFrame:
    """SK 유동인구 월별 CSV를 이어붙여 반환.

    kind: 'flow_age_pop' | 'flow_time_pop' | 'flow_wkdy_pop'
    """
    if kind not in C.SK_KINDS:
        raise ValueError(f"kind must be one of {C.SK_KINDS}, got {kind!r}")
    months = months or C.SK_MONTHS
    frames = []
    for ym in months:
        path = C.SK_DIR / f"{kind}_{ym}.csv"
        frames.append(pd.read_csv(path, **{**C.SK_READ_KWARGS, **kwargs}))
    df = pd.concat(frames, ignore_index=True)
    # 202512의 time·wkdy 파일은 전체 행이 정확히 2번씩 들어 있다 (운영측 공지,
    # 2026-09 재배포본에서도 그대로). 중복 행의 값이 완전히 동일해 제거가 안전하다.
    return df.drop_duplicates(subset=C.SK_KEYS, ignore_index=True)


def load_shinhan(which: str = "mct", **kwargs) -> pd.DataFrame:
    """신한카드 데이터. which: 'mct'(가맹점 기준) | 'cln'(고객 거주지 기준)."""
    path = {"mct": C.SHINHAN_MCT, "cln": C.SHINHAN_CLN}[which]
    return pd.read_csv(path, **{**C.SHINHAN_READ_KWARGS, **kwargs})


def cache(df: pd.DataFrame, name: str, stage: str = "interim") -> Path:
    """중간 결과를 parquet으로 저장하고 경로 반환."""
    base = {"interim": C.INTERIM, "processed": C.PROCESSED}[stage]
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{name}.parquet"
    df.to_parquet(path, index=False)
    return path
