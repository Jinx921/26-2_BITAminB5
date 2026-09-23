"""격자 × 자원유형 접근성 테이블 생성 → preprocessed/grid_access.parquet

  python3 notebooks/build_grid_access.py

격자 하나당
  dist_<유형>   최근접 지점까지의 거리(m)
  n300/500/1000_<유형>  반경 내 지점 수 (합쳐진 시설 수 기준)
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import numpy as np, pandas as pd
from scipy.spatial import cKDTree
import config as C
from external import load_external, consolidate, valid_cells

RADII = (300, 500, 1000)
# 분석에 쓸 유형 (판정에서 채택/보조된 것)
KINDS = ['체육시설(공공)', '도서관', '문화시설', '도시공원', '체육시설(민간)']


def main():
    print("[1] 외부 데이터 로드 · 통합")
    ext = consolidate(load_external())
    ext = ext[ext.region.notna()]

    print("\n[2] 분석 대상 격자")
    cells = valid_cells()
    print(cells.groupby('region').size().to_string())

    print("\n[3] 유형별 접근성 계산")
    out = cells.rename(columns={'X_COORD': 'x', 'Y_COORD': 'y',
                                'n': 'n_months', 'mean': 'flow_mean'}).copy()
    out['cell_id'] = out.x.astype('int64').astype(str) + '_' + out.y.astype('int64').astype(str)

    for kind in KINDS:
        dist = pd.Series(np.nan, index=out.index)
        cnt = {r: pd.Series(np.nan, index=out.index) for r in RADII}
        for region, cg in out.groupby('region'):
            eg = ext[(ext.region == region) & (ext.kind == kind)]
            if eg.empty:
                continue                       # 해당 지역에 자원 없음 → NaN 유지
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

    # 기회 자원 통합 (민간 제외)
    pub = [k for k in KINDS if k != '체육시설(민간)']
    for r in RADII:
        cols = [f'n{r}_' + k.replace('(', '_').replace(')', '') for k in pub]
        out[f'opp_n{r}'] = out[cols].fillna(0).sum(axis=1).astype(int)
    dcols = ['dist_' + k.replace('(', '_').replace(')', '') for k in pub]
    out['opp_dist_min'] = out[dcols].min(axis=1).round(1)
    out['opp_kinds_300'] = (out[[f'n300_' + k.replace('(', '_').replace(')', '')
                                 for k in pub]].fillna(0) > 0).sum(axis=1)

    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    path = pathlib.Path('preprocessed'); path.mkdir(exist_ok=True)
    f = path / 'grid_access.parquet'
    out.to_parquet(f, index=False)
    print(f"\n[4] 저장 → {f}  ({len(out):,}행 × {out.shape[1]}열)")
    print("\n통합 지표 요약 (기회 자원 = 민간 체육시설 제외)")
    print(out.groupby('region')[['opp_dist_min', 'opp_n300', 'opp_n500', 'opp_kinds_300']]
             .describe(percentiles=[.25, .5, .75]).T.round(1).to_string())


if __name__ == '__main__':
    main()
