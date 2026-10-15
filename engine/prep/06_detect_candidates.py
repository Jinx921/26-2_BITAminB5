"""활동위축 후보 탐지 (사랑 src/eda_srh.py 재현) -> engine/data/cell_month.parquet, cell_cluster.parquet

1. 칸별 6개월 평균 24시간 비중 → 지역별 표준화 → KMeans(k=8, random_state=42, n_init=20). 10칸 미만 군집 제외
2. 월별 day_share(10~16시 비중) → (지역·군집·월) 안 robust z = (x - 중앙값) / (1.4826·MAD), MAD=0 이면 결측
3. 거주(월) = 야간 비중 ≥ 지역 기준 AND SGIS 주택 수 ≥ 지역 기준(강남 200·춘천 30)
4. 고령 상위 25% = 거주 행(칸·월)의 senior_ratio 75% 분위 이상 (월 단위)
5. 후보 = 거주 & 고령 상위 & z<0 인 달이 4개월 이상
이 스크립트는 월 단위 재료만 저장하고, 기준값별 후보 계산은 core.detect_candidates 가 한다 (강건성 재계산용).
검증: 팀 기준 → 강남 65 / 춘천 192 (srh_07)
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

BASE = Path(__file__).resolve().parents[2]
D = BASE / 'engine' / 'preprocessed'
FLOW = next(p for p in [BASE / 'preprocessed' / 'flow_cell.parquet', D / 'team' / 'flow_cell.parquet'] if p.exists())
MIN_CLUSTER_CELLS = 10

flow = pd.read_parquet(FLOW)
flow['region'] = flow.sgg_nm.map({'강남구': '강남', '춘천시': '춘천'})
prof = [f'p_TMST_{h:02d}' for h in range(24)]
day = [f'p_TMST_{h:02d}' for h in range(10, 17)]

# 1. 군집
feat = flow.groupby(['region', 'cell_id'], as_index=False)[prof].mean()
feat['cluster'] = None
for reg, idx in feat.groupby('region').groups.items():
    X = StandardScaler().fit_transform(feat.loc[idx, prof].fillna(0))
    lab = KMeans(n_clusters=min(8, len(idx)), random_state=42, n_init=20).fit_predict(X)
    feat.loc[idx, 'cluster'] = [f'{reg}_{l + 1}' for l in lab]
size = feat.groupby(['region', 'cluster']).size()
small = set(size[size < MIN_CLUSTER_CELLS].index)
feat['cluster_raw'] = feat.cluster
feat.loc[[(r, c) in small for r, c in zip(feat.region, feat.cluster)], 'cluster'] = np.nan
feat[['region', 'cell_id', 'cluster', 'cluster_raw']].to_parquet(D / 'cell_cluster.parquet', index=False)

# 2. robust z
w = flow.merge(feat[['region', 'cell_id', 'cluster']], on=['region', 'cell_id'], how='left')
w['day_share'] = w[day].sum(axis=1).clip(0, 1)
grp = w.groupby(['region', 'cluster', 'STD_YM'], dropna=True)['day_share']
med = grp.transform('median')
mad = grp.transform(lambda v: np.nanmedian(np.abs(v - np.nanmedian(v))))
w['dev_day_share'] = (w.day_share - med) / (1.4826 * mad).where(mad != 0)

# 3. SGIS 주택 수
cmap = pd.read_parquet(D / 'cell_grid_map.parquet')
sg = pd.read_parquet(D / 'sgis_grid.parquet')[['GRID_CD', 'total_housing', 'senior65_share', 'hh_1p_share']]
w = w.merge(cmap, on=['region', 'cell_id'], how='left').merge(sg, on='GRID_CD', how='left')

cols = ['region', 'cell_id', 'STD_YM', 'cluster', 'day_share', 'dev_day_share', 'night_share', 'senior_ratio',
        'tot_time', 'GRID_CD', 'total_housing']
w[cols].to_parquet(D / 'cell_month.parquet', index=False)

# 팀 기준으로 바로 확인
NIGHT = {'강남': 0.07, '춘천': 0.03}
HOUSE = {'강남': 200, '춘천': 30}
res = (w.night_share >= w.region.map(NIGHT)) & (w.total_housing >= w.region.map(HOUSE))
thr = w[res].groupby('region').senior_ratio.quantile(.75)
top = w.senior_ratio >= w.region.map(thr)
cnt = w[res & top & (w.dev_day_share < 0)].groupby(['region', 'cell_id']).STD_YM.nunique()
cand = cnt[cnt >= 4]
print('군집 크기(10칸 미만 제외):', {k: v for k, v in small} if small else '없음')
print('후보(팀 기준 재현):', cand.groupby(level=0).size().to_dict(), '| 팀 srh_07: 강남 65 / 춘천 192')
team = pd.read_parquet(D / 'team' / 'srh_07_candidate_cells.parquet')
mine = set(cand.index)
teams = set(zip(team.region, team.cell_id))
print('팀 목록과 겹침:', len(mine & teams), '/ 팀', len(teams), '/ 엔진', len(mine))
