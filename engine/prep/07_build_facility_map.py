# 시설 지도 파일: 엔진이 거리 계산에 쓰는 시설(교류·보건)만 점 GeoJSON으로 내보낸다
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C

PROPS = ['fac_id', 'name', 'kind', 'group', 'addr']

fac = pd.read_parquet(C.ROOT / 'preprocessed' / 'facility.parquet')
fac = fac[fac.group.isin(['social', 'health'])]          # excluded(민간 체육)는 엔진 계산에 안 쓰므로 뺀다

for region, f in fac.groupby('region'):
    feats = [{'type': 'Feature',
              'geometry': {'type': 'Point', 'coordinates': [round(r.lon, 6), round(r.lat, 6)]},
              'properties': {k: getattr(r, k) for k in PROPS}}
             for r in f.itertuples()]
    p = C.OUT / f'facilities_{region}.geojson'
    p.write_text(json.dumps({'type': 'FeatureCollection', 'features': feats}, ensure_ascii=False), encoding='utf-8')
    print(p.name, len(feats), f.groupby(['group', 'kind']).size().to_dict())
