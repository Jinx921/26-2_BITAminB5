"""시설 통합 테이블 -> engine/data/facility.parquet

자원 범위 (5차 회의 확정): 경로당·마을회관 / 보건(보건소·지소·분소·진료소) / 도서관 / 공공체육 / 문화
제외: 민간체육(신고), 도시공원(커버리지 불균등), 사회복지시설(좌표 없음)
규칙은 팀 코드(src/external.py, build_grid_welfare_access.py)를 따른다.
  - 체육시설: faci_gb_nm 공공/신고 분리, 공공만 사용
  - 공공시설개방: 문화재단·예술·연습공간·공연 -> 문화시설, 나머지 -> 체육시설(공공)
  - 같은 유형 10m 안 중복은 한 지점으로 (n_at_point 보존)
  - 경로당: 영업 중만, 위도=경도 좌표 오류 제외
팀 규칙과 다른 점 (EXCLUDE_CLOSED_SPORTS=True): 체육시설 폐업 제외
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from pyproj import Transformer

BASE = Path(__file__).resolve().parents[2]
RAW = BASE / 'data' / 'external' / 'facilities' / 'raw'
OUT = BASE / 'engine' / 'preprocessed' / 'facility.parquet'
EXCLUDE_CLOSED_SPORTS = '--team' not in sys.argv   # --team 이면 팀 결과 재현용

TF = Transformer.from_crs('EPSG:4326', 'EPSG:5179', always_xy=True)
CULTURE = '문화재단|예술|연습공간|공연'


def read(name):
    for enc in ('utf-8-sig', 'cp949', 'euc-kr'):
        try:
            return pd.read_csv(RAW / name, encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise ValueError(name)


def s(col):
    """결측을 빈 문자열로 (pandas 3.0은 astype(str) 후에도 결측이 남아 이어붙이면 전체가 결측이 됨)"""
    return col.fillna('').astype(str)


def region_of(text):
    t = text.fillna('').astype(str)
    return np.select([t.str.contains('강남구'), t.str.contains('춘천')], ['강남', '춘천'], None)


def frame(kind, name, addr, lat, lon, source, extra=None):
    d = pd.DataFrame({'kind': kind, 'name': name, 'addr': addr,
                      'lat': pd.to_numeric(lat, errors='coerce'),
                      'lon': pd.to_numeric(lon, errors='coerce'), 'source': source})
    if extra is not None:
        d['region'] = extra
    return d


parts = []

# 1) 경로당·마을회관
for f, reg in [('서울특별시_강남구_마을회관및경로당.csv', '강남'), ('강원특별자치도_춘천시_마을회관및경로당.csv', '춘천')]:
    d = read(f)
    d = d[d['영업상태명'].eq('영업') & (d['위도'] != d['경도'])]
    parts.append(frame('경로당', d['시설명'], d['소재지도로명주소'], d['위도'], d['경도'], f, reg))

# 2) 보건
d = read('보건관련기관_좌표_데이터.csv')
parts.append(frame('보건', d.FACILITY_NAME, d.ADDRESS, d.LATITUDE, d.LONGITUDE,
                   '보건관련기관_좌표_데이터.csv', d.REGION.map({'강남구': '강남', '춘천시': '춘천'})))

# 3) 체육시설 (공공만)
d = read('전국체육시설표준데이터_api.csv')
if EXCLUDE_CLOSED_SPORTS:
    d = d[d.faci_stat_nm.ne('폐업')]
kind = np.where(d.faci_gb_nm.eq('공공'), '체육시설(공공)', '체육시설(민간)')
parts.append(frame(kind, d.faci_nm, d.faci_road_addr, d.faci_lat, d.faci_lot, '전국체육시설표준데이터_api.csv',
                   region_of(s(d.cpb_nm) + ' ' + s(d.faci_road_addr))))

# 4) 도서관
d = read('전국도서관표준데이터.csv')
parts.append(frame('도서관', d['도서관명'], d['소재지도로명주소'], d['위도'], d['경도'], '전국도서관표준데이터.csv',
                   region_of(s(d['시군구명']) + ' ' + s(d['소재지도로명주소']))))

# 5) 문화 (박물관·미술관)
d = read('전국박물관미술관정보표준데이터.csv')
parts.append(frame('문화시설', d['시설명'], d['소재지도로명주소'], d['위도'], d['경도'], '전국박물관미술관정보표준데이터.csv',
                   region_of(s(d['소재지도로명주소']) + ' ' + s(d['소재지지번주소']))))

# 6) 공공시설개방 -> 문화 / 체육(공공)
d = read('전국공공시설개방정보표준데이터.csv')
txt = s(d['관리기관명']) + ' ' + s(d['개방시설명']) + ' ' + s(d['개방장소명'])
kind = np.where(txt.str.contains(CULTURE, na=False), '문화시설', '체육시설(공공)')
parts.append(frame(kind, d['개방시설명'], d['소재지도로명주소'], d['위도'], d['경도'], '전국공공시설개방정보표준데이터.csv',
                   region_of(s(d['소재지도로명주소']) + ' ' + s(d['소재지지번주소']))))

fac = pd.concat(parts, ignore_index=True)
fac = fac[fac.region.notna() & fac.lat.between(33, 39) & fac.lon.between(124, 132)].copy()
fac['x'], fac['y'] = TF.transform(fac.lon.to_numpy(), fac.lat.to_numpy())

# 같은 유형 10m 안 중복 병합
fac['_px'] = (fac.x / 10).round().astype('int64')
fac['_py'] = (fac.y / 10).round().astype('int64')
key = ['kind', 'region', '_px', '_py']
fac['n_at_point'] = fac.groupby(key).x.transform('size')
fac = fac.drop_duplicates(key).drop(columns=['_px', '_py']).reset_index(drop=True)

fac['group'] = fac.kind.map({'경로당': 'social', '도서관': 'social', '체육시설(공공)': 'social', '문화시설': 'social',
                             '보건': 'health', '체육시설(민간)': 'excluded'})
fac['fac_id'] = fac.region.map({'강남': 'GN', '춘천': 'CC'}) + '_' + fac.index.astype(str).str.zfill(5)

print('모드:', '엔진 기본(체육 폐업 제외)' if EXCLUDE_CLOSED_SPORTS else '팀 재현(폐업 포함)')
print('지점 수 (시설 수)')
summ = fac.groupby(['region', 'kind']).agg(지점=('fac_id', 'size'), 시설=('n_at_point', 'sum')).unstack(0)
print(summ.to_string())

OUT.parent.mkdir(parents=True, exist_ok=True)
if EXCLUDE_CLOSED_SPORTS:
    fac.to_parquet(OUT, index=False)
    print('저장 ->', OUT.relative_to(BASE), len(fac), '행')
else:
    fac.to_parquet(OUT.with_name('facility_teamrepro.parquet'), index=False)
