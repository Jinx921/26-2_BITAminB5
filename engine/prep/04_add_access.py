"""칸별 자원 접근성 -> engine/data/cell_master.parquet

facility.parquet 로 칸 중심에서 유형별 최근접 거리·반경 내 개수를 계산한다.
교류(social) = 경로당·마을회관 + 도서관 + 체육시설(공공) + 문화시설
보건(health) = 보건소·지소·분소·진료소
같은 도시 시설만 쓴다 (팀 코드와 동일, 도시 간 비교 안 함)
"""
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.spatial import cKDTree

BASE = Path(__file__).resolve().parents[2]
D = BASE / 'engine' / 'preprocessed'
KINDS = {'경로당': 'senior', '도서관': 'library', '체육시설(공공)': 'sports', '문화시설': 'culture', '보건': 'health'}
RADII = (500, 1000, 3000)

c = pd.read_parquet(D / 'cells_resid.parquet')
fac = pd.read_parquet(D / 'facility.parquet')

for kind, tag in list(KINDS.items()) + [('__social__', 'social')]:
    dist = np.full(len(c), np.nan)
    cnt = {r: np.zeros(len(c), dtype=int) for r in RADII}
    for reg, idx in c.groupby('region').groups.items():
        if kind == '__social__':
            f = fac[(fac.region == reg) & (fac.group == 'social')]
        else:
            f = fac[(fac.region == reg) & (fac.kind == kind)]
        tree = cKDTree(f[['x', 'y']].to_numpy())
        pts = c.loc[idx, ['x', 'y']].to_numpy()
        d, _ = tree.query(pts, k=1)
        pos = c.index.get_indexer(idx)
        dist[pos] = d
        w = f.n_at_point.to_numpy()
        for r in RADII:
            cnt[r][pos] = [int(w[i].sum()) for i in tree.query_ball_point(pts, r)]
    c[f'dist_{tag}'] = dist.round(1)
    for r in RADII:
        c[f'n{r}_{tag}'] = cnt[r]

c.to_parquet(D / 'cell_master.parquet', index=False)
print('교류·보건 최근접 거리 중앙값(m)')
print(c.groupby('region')[['dist_social', 'dist_senior', 'dist_health']].median().round(0).to_string())
print('\n저장 ->', (D / 'cell_master.parquet').relative_to(BASE), c.shape)
