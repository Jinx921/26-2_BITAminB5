"""SGIS 1km 격자 통계 -> engine/data/sgis_grid.parquet, cell_grid_map.parquet

자료: 공공데이터포털 "국가데이터처_SGIS 격자 통계 및 경계"(2024 통계, 2025.6.30 경계) 중 다사·라사·라아 도엽
팀 산식(src/eda_sgis.py build_sgis_grid)과 같게 계산한다.
  - 칸 → 1km 격자: flow_cell 좌표가 속한 격자 (팀과 같은 기준점)
  - 결측(비밀보호)은 0 으로 (팀과 동일)
검증: 강남 57격자 총인구 695,382 / 춘천 931격자 293,511 (팀 srh_01 과 일치)
"""
from pathlib import Path
import glob

import geopandas as gpd
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
SG = BASE / 'data' / 'external' / 'sgis'
D = BASE / 'engine' / 'preprocessed'
FLOW = next(p for p in [BASE / 'preprocessed' / 'flow_cell.parquet', D / 'team' / 'flow_cell.parquet'] if p.exists())

grid = pd.concat([gpd.read_file(f) for f in glob.glob(str(SG / '2. 경계' / 'grid_*' / '*.shp'))])
grid = gpd.GeoDataFrame(grid, crs=grid.crs).to_crs(5179)

st = []
for kind in ('인구', '가구', '주택'):
    for f in glob.glob(str(SG / '1. 통계' / f'*{kind}*' / '*.csv')):
        d = pd.read_csv(f, encoding='cp949')
        d.columns = ['year', 'GRID_CD', 'item', 'value']
        st.append(d)
st = pd.concat(st)
st['value'] = pd.to_numeric(st.value, errors='coerce')
wide = st.pivot_table(index='GRID_CD', columns='item', values='value', aggfunc='sum')

flow = pd.read_parquet(FLOW)
flow['region'] = flow.sgg_nm.map({'강남구': '강남', '춘천시': '춘천'})
pts = flow[['region', 'cell_id', 'x', 'y']].drop_duplicates(['region', 'cell_id'])
pts = gpd.GeoDataFrame(pts, geometry=gpd.points_from_xy(pts.x, pts.y), crs=5179)
cmap = gpd.sjoin(pts, grid[['GRID_CD', 'geometry']], how='left', predicate='within')[['region', 'cell_id', 'GRID_CD']]

g = pd.DataFrame(index=cmap.GRID_CD.dropna().unique())
w = wide.reindex(g.index).fillna(0)
age = [f'in_age_{i:03d}' for i in range(1, 22)]
g['total_pop'] = w.get('to_in_001', 0)
g['total_household'] = w.get('to_ga_001', 0)
g['total_housing'] = w.get('to_ho_001', 0)
g['age_total'] = w.reindex(columns=age).fillna(0).sum(axis=1)
g['senior65'] = w.reindex(columns=age[13:]).fillna(0).sum(axis=1)          # 65~69세 이상 (in_age_014~021)
g['one_person_household'] = w.get('ga_sd_005', 0)
g['apartment_house'] = w.get('ho_gb_003', 0)
g['detached_house'] = w.get('ho_gb_002', 0)
g['senior65_share'] = (g.senior65 / g.age_total.replace(0, np.nan)).clip(0, 1)
g['hh_1p_share'] = g.one_person_household / g.total_household.replace(0, np.nan)
g['apt_share'] = g.apartment_house / g.total_housing.replace(0, np.nan)
g['detached_share'] = g.detached_house / g.total_housing.replace(0, np.nan)
g['reliable_senior65'] = g.age_total >= 200
g['reliable_hh_1p'] = g.total_household >= 50
g = g.rename_axis('GRID_CD').reset_index()

g.to_parquet(D / 'sgis_grid.parquet', index=False)
cmap.to_parquet(D / 'cell_grid_map.parquet', index=False)
chk = cmap.merge(g, on='GRID_CD').drop_duplicates('GRID_CD').groupby('region').agg(격자=('GRID_CD', 'size'), 총인구=('total_pop', 'sum'))
print('칸→격자 매칭률', cmap.GRID_CD.notna().mean().round(4))
print(chk.to_string())
