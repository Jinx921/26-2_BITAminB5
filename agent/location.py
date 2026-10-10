"""시민 위치 → 서비스 지역 판단 (코드가 판단한다. Sonnet 은 관여하지 않는다).

앱이 넘겨준 위도·경도를 엔진 칸 ID 로 바꾸고, 엔진 공개 도구 lookup_resources 에 칸 ID 를 넣어
어느 지역의 칸인지 확인한다. 엔진은 다른 지역 칸이면 result.error 를 돌려준다.
자기 칸이 격자에 없으면(통신 기록이 없는 칸) 바로 옆 칸까지 확인한다.
"""
from __future__ import annotations

from pyproj import Transformer

from agent.engine_client import EngineError

# 엔진 칸 ID 규칙: UTM-K(EPSG:5179) 좌표를 칸 크기(250m)로 나눈 몫 "x_y" (예시 응답의 칸 좌표로 테스트가 확인한다)
CELL_M = 250
NEIGHBOR_RING = 1            # 자기 칸이 없을 때 확인할 옆 칸 범위 (1 = 250m)
_TO_UTMK = Transformer.from_crs('EPSG:4326', 'EPSG:5179', always_xy=True)


def cell_of(lat: float, lon: float) -> tuple[int, int]:
    x, y = _TO_UTMK.transform(lon, lat)
    return int(x // CELL_M), int(y // CELL_M)


def _in_region(engine, region: str, cx: int, cy: int) -> bool:
    try:
        res = engine.call('lookup_resources', {'region': region, 'cell_id': f'{cx}_{cy}'})
    except EngineError:
        return False
    return 'error' not in res['result']


def detect_region(engine, lat: float, lon: float, regions: list[str]) -> str | None:
    """위치가 속한 서비스 지역. 어느 지역도 아니면 None."""
    cx, cy = cell_of(lat, lon)
    for k in range(NEIGHBOR_RING + 1):
        ring = [(cx + dx, cy + dy) for dx in range(-k, k + 1) for dy in range(-k, k + 1) if max(abs(dx), abs(dy)) == k]
        for region in regions:
            if any(_in_region(engine, region, x, y) for x, y in ring):
                return region
    return None
