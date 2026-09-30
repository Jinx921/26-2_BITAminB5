"""격자 × 자원유형 접근성 테이블 → preprocessed/grid_access.parquet

  python3 notebooks/build_grid_access.py

**격자 단위는 팀 표준인 250m(`preprocessed/flow_cell.parquet`)를 따른다.**
cell_id = floor(X/250)_floor(Y/250) 이며, 거리 계산의 기준점은 격자 중심
(floor*250 + 125)이다. 채원의 복지시설 접근성과 같은 기준이라 결과를 바로 합칠 수 있다.

격자 하나당
  dist_<유형>            최근접 지점까지의 거리(m)
  n300/500/1000_<유형>   반경 내 시설 수
  opp_*                  통합 기회 자원 (민간 체육시설·도시공원 제외)
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import numpy as np, pandas as pd
from scipy.spatial import cKDTree
import config as C
from external import load_external, consolidate

RADII = (300, 500, 1000)
KINDS = ['체육시설(공공)', '도서관', '문화시설', '도시공원', '체육시설(민간)']
CELL_M = 250


def team_cells() -> pd.DataFrame:
    """팀 표준 250m 격자. flow_cell.parquet 의 6개월치를 격자 단위로 요약한다."""
    f = pd.read_parquet(C.ROOT / 'preprocessed' / 'flow_cell.parquet')
    f['region'] = f.sgg_nm.map({'강남구': '강남', '춘천시': '춘천'})
    g = (f.groupby(['region', 'cell_id'])
           .agg(n_months=('STD_YM', 'nunique'),
                flow_mean=('tot_age', 'mean'),
                senior_ratio=('senior_ratio', 'mean'),
                night_share=('night_share', 'mean'),
                weekend_ratio=('weekend_ratio', 'mean'),
                peer=('peer', 'first'),
                neg_months=('neg_months', 'first'),
                trend=('trend', 'first'))
           .reset_index())
    # cell_id → 격자 중심 좌표 (채원과 동일 기준)
    ij = g.cell_id.str.split('_', expand=True).astype('int64')
    g['x'] = ij[0] * CELL_M + CELL_M / 2
    g['y'] = ij[1] * CELL_M + CELL_M / 2
    g['senior_ratio'] = (g.senior_ratio * 100).round(2)   # % 로 통일
    return g


def candidates() -> pd.DataFrame:
    """사랑의 활동위축 후보셀 (srh_07). 없으면 빈 프레임."""
    f = C.TABLES / 'srh_07_candidate_cells.csv'
    if not f.exists():
        print("  [건너뜀] srh_07_candidate_cells.csv 없음 — 후보 플래그 미부착")
        return pd.DataFrame(columns=['region', 'cell_id', 'persistent_months'])
    d = pd.read_csv(f, encoding='utf-8-sig')
    return d[['region', 'cell_id', 'persistent_months']].assign(is_candidate=True)


def main():
    print("[1] 외부 데이터 로드 · 통합")
    ext = consolidate(load_external())
    ext = ext[ext.region.notna()]

    print(f"\n[2] 팀 표준 250m 격자 (preprocessed/flow_cell.parquet)")
    cells = team_cells()
    print(cells.groupby('region').agg(격자수=('cell_id', 'size'),
                                      일평균유동인구_중앙값=('flow_mean', 'median')).round(1).to_string())

    cand = candidates()
    if len(cand):
        cells = cells.merge(cand, on=['region', 'cell_id'], how='left')
        cells['is_candidate'] = cells.is_candidate.fillna(False)
        print(f"  사랑 후보셀 결합: {int(cells.is_candidate.sum())}개")

    print("\n[3] 유형별 접근성 계산 (격자 중심 기준)")
    out = cells.copy()
    for kind in KINDS:
        dist = pd.Series(np.nan, index=out.index)
        cnt = {r: pd.Series(np.nan, index=out.index) for r in RADII}
        for region, cg in out.groupby('region'):
            eg = ext[(ext.region == region) & (ext.kind == kind)]
            if eg.empty:
                continue
            tree = cKDTree(eg[['x', 'y']].to_numpy())
            pts = cg[['x', 'y']].to_numpy()
            d, _ = tree.query(pts, k=1)
            dist.loc[cg.index] = d
            w = eg.n_at_point.to_numpy()
            for r in RADII:
                idx = tree.query_ball_point(pts, r)
                cnt[r].loc[cg.index] = [int(w[i].sum()) if len(i) else 0 for i in idx]
        tag = kind.replace('(', '_').replace(')', '')
        out[f'dist_{tag}'] = dist.round(1)
        for r in RADII:
            out[f'n{r}_{tag}'] = cnt[r]
        ok = dist.notna().groupby(out.region).mean() * 100
        print(f"  {kind:<12} 계산된 격자 비율: " +
              " / ".join(f"{k} {v:.0f}%" for k, v in ok.items()))

    # 기회 자원 통합 지표.
    #  - 민간 체육시설 제외: '사회적 관계를 만들 기회'로 보기 어렵다.
    #  - 도시공원 제외: 전국표준데이터가 지자체 등록에 의존해 커버리지가 불균등하다.
    EXCLUDE = {'체육시설(민간)', '도시공원'}
    pub = [k for k in KINDS if k not in EXCLUDE]
    print(f"\n[통합 지표 구성] {' + '.join(pub)}  (제외: {', '.join(sorted(EXCLUDE))})")
    for r in RADII:
        cols = [f'n{r}_' + k.replace('(', '_').replace(')', '') for k in pub]
        out[f'opp_n{r}'] = out[cols].fillna(0).sum(axis=1).astype(int)
    dcols = ['dist_' + k.replace('(', '_').replace(')', '') for k in pub]
    out['opp_dist_min'] = out[dcols].min(axis=1).round(1)
    out['opp_kinds_300'] = (out[[f'n300_' + k.replace('(', '_').replace(')', '')
                                 for k in pub]].fillna(0) > 0).sum(axis=1)

    f = pathlib.Path('preprocessed/grid_access.parquet')
    out.to_parquet(f, index=False)
    print(f"\n[4] 저장 → {f}  ({len(out):,}행 × {out.shape[1]}열)")
    print("\n통합 지표 요약")
    print(out.groupby('region')[['opp_dist_min', 'opp_n300', 'opp_n500', 'opp_kinds_300']]
             .describe(percentiles=[.25, .5, .75]).T.round(1).to_string())


if __name__ == '__main__':
    main()
