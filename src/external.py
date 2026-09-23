"""외부 데이터(사회적 기회 자원) 로딩 · 좌표 변환 · 격자 접근성 평가.

data/external/ 에 공공데이터포털 표준데이터 CSV를 그대로 넣으면 된다.
파일명은 자유. 아래 SOURCES 의 키워드로 자동 인식한다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config as C

# 파일명에 포함되면 해당 유형으로 인식할 키워드
SOURCES = {
    '도서관': ['도서관'],
    '도시공원': ['도시공원', '공원정보'],
    '체육시설': ['체육시설'],
    '공공시설개방': ['공공시설개방', '시설개방'],
    '박물관미술관': ['박물관', '미술관'],
    '실외운동기구': ['실외운동기구', '운동기구'],
    '사회복지시설': ['사회복지시설'],
    '경로당': ['경로당', '마을회관'],
}

# 표준데이터마다 컬럼명이 조금씩 다르다. 후보를 넓게 둔다.
LAT = ['위도', 'faci_lat', 'latitude', 'LAT', 'lat', '위도(EPSG:4326)']
LON = ['경도', 'faci_lot', 'faci_lon', 'longitude', 'LON', 'lon', 'lng', '경도(EPSG:4326)']
SIDO = ['시도명', 'cp_nm', '시도', '소재지시도명']
SGG = ['시군구명', 'jrsdSggNm', 'cpb_nm', '시군구', '소재지시군구명']
NAME = ['시설명', 'fcltNm', 'faci_nm', '도서관명', '공원명', '박물관미술관명', '사회복지시설명', '명칭', '개방장소명']
ADDR = ['소재지도로명주소', 'fcltAddr', 'faci_road_addr', 'faci_addr', '소재지지번주소', '도로명주소', '지번주소', '주소']

TARGET_SGG = {'강남구': '강남', '춘천시': '춘천'}

# 유형 안에서 다시 갈라야 하는 경우.
#   {유형: (구분컬럼 후보, {원본값: 붙일 접미사})}
# 체육시설의 faci_gb_nm 은 '공공' / '신고'(민간 사업자 신고) 로 나뉜다.
# 민간 체력단련장·당구장은 '사회적 기회 자원'으로 보기 어려워 분리한다.
KIND_SPLIT = {
    '체육시설': (['faci_gb_nm', '시설구분명'], {'공공': '공공', '신고': '민간'}),
}


def _pick(df: pd.DataFrame, cands: list[str]) -> str | None:
    for c in cands:
        if c in df.columns:
            return c
    return None


def _read(path):
    """공공데이터포털 CSV는 CP949가 대부분이고 가끔 UTF-8(BOM)이다."""
    for enc in ('cp949', 'utf-8-sig', 'euc-kr'):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise ValueError(f'인코딩을 못 찾음: {path}')


def load_external() -> pd.DataFrame:
    """data/external/*.csv 를 모두 읽어 표준 스키마로 반환.

    columns: kind, name, sido, sgg, region, addr, lat, lon, x, y
    """
    from pyproj import Transformer
    tf = Transformer.from_crs('EPSG:4326', C.SK_CRS, always_xy=True)

    rows = []
    for path in sorted(C.EXTERNAL.glob('*.csv')):
        kind = next((k for k, keys in SOURCES.items()
                     if any(w in path.name for w in keys)), None)
        if kind is None:
            print(f'  [건너뜀] 유형 미인식: {path.name}')
            continue
        df = _read(path)
        lat, lon = _pick(df, LAT), _pick(df, LON)
        if not lat or not lon:
            print(f'  [건너뜀] 위경도 컬럼 없음: {path.name} → {list(df.columns)[:12]}')
            continue
        out = pd.DataFrame({
            'kind': kind,
            'name': df[_pick(df, NAME)] if _pick(df, NAME) else '',
            'sido': df[_pick(df, SIDO)] if _pick(df, SIDO) else '',
            'sgg': df[_pick(df, SGG)] if _pick(df, SGG) else '',
            'addr': df[_pick(df, ADDR)] if _pick(df, ADDR) else '',
            'lat': pd.to_numeric(df[lat], errors='coerce'),
            'lon': pd.to_numeric(df[lon], errors='coerce'),
        })
        # 유형 내부 분할 (예: 체육시설 → 공공 / 민간)
        if kind in KIND_SPLIT:
            cands, mapping = KIND_SPLIT[kind]
            col = _pick(df, cands)
            if col:
                suffix = df[col].map(mapping).fillna('기타')
                out['kind'] = kind + '(' + suffix + ')'
                print('        분할: ' + ' / '.join(
                    f'{k} {v:,}' for k, v in out['kind'].value_counts().items()))
            else:
                print(f'        [경고] 분할 컬럼 없음 ({cands}) — 분할 안 함')
        out['_file'] = path.name
        rows.append(out)
        print(f'  [읽음] {path.name}: {len(out):,}행 → {kind}')

    if not rows:
        raise FileNotFoundError(f'{C.EXTERNAL} 에 읽을 CSV가 없다')
    d = pd.concat(rows, ignore_index=True)

    # 대상 지역만: 시군구명 우선, 없으면 주소 문자열로 판정
    key = d.sgg.fillna('').astype(str) + ' ' + d.addr.fillna('').astype(str)
    d['region'] = np.select(
        [key.str.contains('강남구'), key.str.contains('춘천')],
        ['강남', '춘천'], default=None)

    d = d.dropna(subset=['lat', 'lon'])
    d = d[(d.lat.between(33, 39)) & (d.lon.between(124, 132))]   # 한반도 범위 밖 제거
    x, y = tf.transform(d.lon.values, d.lat.values)
    d['x'], d['y'] = x, y
    return d.reset_index(drop=True)


def valid_cells(min_mean: float = 30.0) -> pd.DataFrame:
    """분석 대상 격자: 6개월 완전관측 + 일평균 min_mean 이상."""
    from loaders import load_sk
    AGE = [f'{p}_FLOW_POP_CNT_{g}' for p in ['MAN', 'WMAN']
           for g in ['10G', '20G', '30G', '40G', '50G', '60GU']]
    a = load_sk('flow_age_pop')
    a['total'] = a[AGE].sum(axis=1)
    a['region'] = np.where(a.X_COORD < 1_000_000, '강남', '춘천')
    g = (a.groupby(['region', 'X_COORD', 'Y_COORD'])
           .agg(n=('total', 'size'), mean=('total', 'mean')).reset_index())
    return g[(g.n == 6) & (g['mean'] >= min_mean)].reset_index(drop=True)


def accessibility(ext: pd.DataFrame, cells: pd.DataFrame,
                  radii=(300, 500, 1000)) -> pd.DataFrame:
    """격자별 최근접 거리와 반경 내 개수. 유형 × 지역별로 계산."""
    from scipy.spatial import cKDTree
    res = []
    for region, cg in cells.groupby('region'):
        pts = cg[['X_COORD', 'Y_COORD']].to_numpy()
        for kind, eg in ext[ext.region == region].groupby('kind'):
            if eg.empty:
                continue
            tree = cKDTree(eg[['x', 'y']].to_numpy())
            dist, _ = tree.query(pts, k=1)
            row = {'region': region, 'kind': kind,
                   '시설수': len(eg), '격자수': len(cg),
                   '최근접거리_중앙값m': round(float(np.median(dist)), 1)}
            for r in radii:
                row[f'{r}m내_격자비율%'] = round(
                    float((dist <= r).mean()) * 100, 1)
            res.append(row)
    return pd.DataFrame(res)
