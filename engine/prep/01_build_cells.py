"""250m 칸 기본 테이블 -> engine/data/cells_base.parquet

재료: 팀 flow_cell.parquet(250m x 월), 팀 후보 srh_07, SKT 원본(행정동 부여용)
- 칸 좌표는 격자 중심 (floor*250 + 125), 팀 표준
- 월 지표는 6개월 평균, 이탈 지표(neg_months, trend, peer)는 칸 고정값
- 행정동(emd8): 칸 안 50m 원본 셀의 BLOCK_CD 앞 8자리 중 최빈값
"""
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parents[2]
TEAM = BASE / 'engine' / 'preprocessed' / 'team'
SKT = BASE / 'data' / 'layout' / 'skt'
OUT = BASE / 'engine' / 'preprocessed' / 'cells_base.parquet'
CELL = 250

f = pd.read_parquet(next(p for p in [BASE / 'preprocessed' / 'flow_cell.parquet', TEAM / 'flow_cell.parquet'] if p.exists()))
f['region'] = f.sgg_nm.map({'강남구': '강남', '춘천시': '춘천'})
f['day_share'] = f.day / f.tot_time
c = (f.groupby(['region', 'cell_id'])
       .agg(sgg5=('sgg_cd', 'first'), n_months=('STD_YM', 'nunique'),
            flow_mean=('tot_age', 'mean'), senior_mean=('senior', 'mean'),
            senior_ratio=('senior_ratio', 'mean'), night_share=('night_share', 'mean'),
            day_share=('day_share', 'mean'), weekend_ratio=('weekend_ratio', 'mean'),
            peer=('peer', 'first'), neg_months=('neg_months', 'first'), trend=('trend', 'first'))
       .reset_index())
ij = c.cell_id.str.split('_', expand=True).astype('int64')
c['x'] = ij[0] * CELL + CELL / 2
c['y'] = ij[1] * CELL + CELL / 2

cand = pd.read_parquet(TEAM / 'srh_07_candidate_cells.parquet')
cand = cand[['region', 'cell_id', 'persistent_months', 'cluster']].assign(is_candidate=True)
c = c.merge(cand, on=['region', 'cell_id'], how='left')
c['is_candidate'] = c.is_candidate.eq(True)

# 행정동 부여 (최빈값) + 두 동 걸침 여부
a = pd.read_csv(SKT / 'flow_age_pop_202512.csv', sep='|', dtype={'BLOCK_CD': str},
                usecols=['BLOCK_CD', 'X_COORD', 'Y_COORD']).drop_duplicates()
a = a[a.BLOCK_CD.str[:5].isin(['11230', '32010'])]
a['cell_id'] = (a.X_COORD // CELL).astype(int).astype(str) + '_' + (a.Y_COORD // CELL).astype(int).astype(str)
a['emd8'] = a.BLOCK_CD.str[:8]
emd = (a.groupby(['cell_id', 'emd8']).size().rename('n').reset_index()
         .sort_values(['cell_id', 'n'], ascending=[True, False]))
n_emd = emd.groupby('cell_id').emd8.nunique().rename('n_emd')
emd = emd.drop_duplicates('cell_id')[['cell_id', 'emd8']]
c = c.merge(emd, on='cell_id', how='left').merge(n_emd, on='cell_id', how='left')
c['boundary_emd'] = c.n_emd.fillna(1) > 1

OUT.parent.mkdir(parents=True, exist_ok=True)
c.to_parquet(OUT, index=False)
print('칸 수', c.groupby('region').size().to_dict())
print('후보', c.groupby('region').is_candidate.sum().to_dict())
print('행정동 부여율', c.emd8.notna().mean().round(3), '| 행정동 수', c.groupby('region').emd8.nunique().to_dict())
print('두 동 걸침 비율', c.groupby('region').boundary_emd.mean().round(3).to_dict())
