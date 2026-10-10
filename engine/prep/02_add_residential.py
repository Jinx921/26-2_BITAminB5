"""칸별 주거 판정 -> engine/data/cells_resid.parquet

GIS 건물통합정보(AL_D010) 건물 좌표를 250m 칸에 넣어 센다.
  A8 건축물용도코드 앞 2자리: 01 단독주택, 02 공동주택, 결측 = 용도 미상
  A13 사용승인일자 (A22는 데이터기준일자라 쓰지 않음)
판정 res_status: 주거 / 용도미상 / 비주거 / 건물없음
  - 용도미상은 아파트일 수 있어 제외하지 않고 태그로 남긴다 (9/30 결정)
"""
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parents[2]
GB = BASE / 'data' / 'external' / 'gis_building'
IN = BASE / 'engine' / 'preprocessed' / 'cells_base.parquet'
OUT = BASE / 'engine' / 'preprocessed' / 'cells_resid.parquet'
CELL = 250

parts = []
for f, reg in [('gangnam_bldg.parquet', '강남'), ('chuncheon_bldg.parquet', '춘천')]:
    b = pd.read_parquet(GB / f, columns=['A8', 'A13', 'x_utmk', 'y_utmk'])
    b['cell_id'] = (b.x_utmk // CELL).astype(int).astype(str) + '_' + (b.y_utmk // CELL).astype(int).astype(str)
    use = b.A8.astype(str).str[:2]
    b['is_res'] = use.isin(['01', '02'])
    b['is_apt'] = use.eq('02')
    b['is_na'] = b.A8.isna()
    b['is_semi'] = use.isin(['14', '04'])        # 업무시설(오피스텔)·2종근생(고시원) 가능
    # 연도는 문자열 앞 4자리로 읽고 1900년 이전(예: 자리표시 '1111-11-11')은 결측. pandas 버전별 날짜 파싱 차이 제거
    yr = pd.to_numeric(b.A13.astype(object).where(b.A13.notna()).astype(str).str[:4], errors='coerce')
    yr = yr.where(yr >= 1900)
    b['old30'] = (yr <= 1995) & b.is_res
    b['yr_ok'] = yr.notna() & b.is_res
    g = b.groupby('cell_id').agg(n_bldg=('A8', 'size'), n_res=('is_res', 'sum'), n_apt=('is_apt', 'sum'),
                                 n_na=('is_na', 'sum'), n_semi=('is_semi', 'sum'),
                                 n_old=('old30', 'sum'), n_yr=('yr_ok', 'sum')).reset_index()
    g['region'] = reg
    parts.append(g)
r = pd.concat(parts)

c = pd.read_parquet(IN).merge(r, on=['region', 'cell_id'], how='left')
for col in ['n_bldg', 'n_res', 'n_apt', 'n_na', 'n_semi', 'n_old', 'n_yr']:
    c[col] = c[col].fillna(0).astype(int)
c['old_share'] = np.where(c.n_yr >= 3, c.n_old / c.n_yr.replace(0, np.nan), np.nan)   # 연도 유효 3채 이상일 때만
c['res_status'] = np.select([c.n_res > 0, c.n_na > 0, c.n_bldg > 0], ['주거', '용도미상', '비주거'], '건물없음')

c.to_parquet(OUT, index=False)
print(pd.crosstab(c.region, c.res_status))
print('\n후보 칸'); print(pd.crosstab(c[c.is_candidate].region, c[c.is_candidate].res_status))
print('\n노후(1995년 이전) 주거 비율 중앙값', c.groupby('region').old_share.median().round(3).to_dict())
