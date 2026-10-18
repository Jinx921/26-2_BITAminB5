"""시민 위치 → 서비스 지역 판단 (코드가 판단한다. Sonnet 은 관여하지 않는다).

앱이 넘겨준 위도·경도를 엔진 칸 ID 로 바꾸고, 엔진 공개 도구 lookup_resources 에 칸 ID 를 넣어
어느 지역의 칸인지 확인한다. 엔진은 다른 지역 칸이면 result.error 를 돌려준다.
자기 칸이 격자에 없으면(통신 기록이 없는 칸) 바로 옆 칸까지 확인한다.
그래도 없으면 시군구 경계(geo/service_area.geojson: 통계청 2018 시군구 경계에서 강남구·춘천시만)로 판단한다.
외곽 마을은 근처에 통신 칸이 없어 춘천인데도 지역 밖으로 나오던 문제 (10/18, 예: 북산면 추전리).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pyproj import Transformer

from agent.engine_client import EngineError

# 엔진 칸 ID 규칙: UTM-K(EPSG:5179) 좌표를 칸 크기(250m)로 나눈 몫 "x_y" (예시 응답의 칸 좌표로 테스트가 확인한다)
CELL_M = 250
NEIGHBOR_RING = 1            # 자기 칸이 없을 때 확인할 옆 칸 범위 (1 = 250m)
_TO_UTMK = Transformer.from_crs('EPSG:4326', 'EPSG:5179', always_xy=True)
BOUNDARY = Path(__file__).resolve().parent / 'geo' / 'service_area.geojson'


def cell_of(lat: float, lon: float) -> tuple[int, int]:
    x, y = _TO_UTMK.transform(lon, lat)
    return int(x // CELL_M), int(y // CELL_M)


def _in_region(engine, region: str, cx: int, cy: int) -> bool:
    try:
        res = engine.call('lookup_resources', {'region': region, 'cell_id': f'{cx}_{cy}'})
    except EngineError:
        return False
    return 'error' not in res['result']


@lru_cache(maxsize=1)
def _boundaries() -> list[tuple[str, list]]:
    """[(지역, [폴리곤 = [바깥 고리, 구멍 고리...]])]. 좌표는 (경도, 위도)."""
    gj = json.loads(BOUNDARY.read_text(encoding='utf-8'))
    out = []
    for f in gj['features']:
        g = f['geometry']
        polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        out.append((f['properties']['region'], polys))
    return out


def _in_ring(lon: float, lat: float, ring: list) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def region_by_boundary(lat: float, lon: float, regions: list[str]) -> str | None:
    """시군구 경계 안에 있으면 그 지역 (구멍 안이면 밖)."""
    for region, polys in _boundaries():
        if region in regions and any(_in_ring(lon, lat, p[0]) and not any(_in_ring(lon, lat, h) for h in p[1:])
                                     for p in polys):
            return region
    return None


def detect_region(engine, lat: float, lon: float, regions: list[str]) -> str | None:
    """위치가 속한 서비스 지역. 어느 지역도 아니면 None."""
    cx, cy = cell_of(lat, lon)
    for k in range(NEIGHBOR_RING + 1):
        ring = [(cx + dx, cy + dy) for dx in range(-k, k + 1) for dy in range(-k, k + 1) if max(abs(dx), abs(dy)) == k]
        for region in regions:
            if any(_in_region(engine, region, x, y) for x, y in ring):
                return region
    return region_by_boundary(lat, lon, regions)
