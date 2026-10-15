"""분석 엔진 호출부. 엔진 코드는 고치지 않고 engine/core.py 의 공개 도구(core.TOOLS)만 부른다.

- LiveEngine:    실제 엔진 계산. 그림을 그리는 도구는 render=False 로 불러 engine/out 의 파일을 덮어쓰지 않는다
                 (지도는 프론트가 결과 행의 lat·lon 으로 그린다).
- FixtureEngine: engine/out/json 예시 응답을 돌려준다. API 키·엔진 데이터 없이 테스트할 때 쓴다.

두 엔진 모두 엔진 공통 형식(tool, region, result, evidence, caveats, figures, geojson, params) dict 를 돌려준다.
"""
from __future__ import annotations

import copy
import importlib
import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = ROOT / 'engine'
FIXTURE_DIR = ENGINE_DIR / 'out' / 'json'

# render 인자를 받는 도구 (그림·geojson 파일을 engine/out 에 쓴다)
RENDER_TOOLS = {'find_candidates', 'classify', 'simulate_placement', 'facility_change'}


class EngineError(Exception):
    """도구 이름이 없거나, 엔진이 예외를 냈거나, 맞는 예시 응답이 없을 때."""


def _normalize_paths(res: dict) -> dict:
    """예시 JSON은 Windows에서 만들어 경로가 out\\x.png 형태다 → out/x.png 로 통일."""
    res['figures'] = [p.replace('\\', '/') for p in res.get('figures') or []]
    if res.get('geojson'):
        res['geojson'] = res['geojson'].replace('\\', '/')
    return res


class LiveEngine:
    name = 'live'

    def __init__(self):
        if str(ENGINE_DIR) not in sys.path:
            sys.path.insert(0, str(ENGINE_DIR))      # 엔진은 `import config` 를 그대로 쓴다
        self._core = importlib.import_module('core')
        self._lock = threading.Lock()                # simulate_placement 가 모듈 전역 상태(_mclp.last_status)를 쓴다

    @property
    def tool_names(self) -> list[str]:
        return list(self._core.TOOLS)

    def call(self, tool: str, args: dict) -> dict:
        fn = self._core.TOOLS.get(tool)
        if fn is None:
            raise EngineError(f'엔진에 없는 도구: {tool}')
        kwargs = dict(args)
        if tool in RENDER_TOOLS:
            kwargs['render'] = False
        try:
            with self._lock:
                res = fn(**kwargs)
        except (TypeError, ValueError, KeyError) as e:   # 잘못된 인자·지역
            raise EngineError(f'{tool} 호출 실패: {e}') from e
        return _normalize_paths(res)


class FixtureEngine:
    """engine/out/json 예시에서 tool·region·params 가 호출 인자와 맞는 응답을 고른다."""
    name = 'fixture'

    def __init__(self, fixture_dir: Path = FIXTURE_DIR):
        self._fixtures = []
        for p in sorted(Path(fixture_dir).glob('*.json')):
            self._fixtures.append((p.name, json.loads(p.read_text(encoding='utf-8'))))

    @property
    def tool_names(self) -> list[str]:
        return sorted({d['tool'] for _, d in self._fixtures})

    @staticmethod
    def _matches(d: dict, tool: str, args: dict) -> bool:
        if d['tool'] != tool:
            return False
        if 'region' in args and d['region'] != args['region']:
            return False
        if tool == 'check_residential':            # params 에 칸 목록이 없어 결과 칸으로 대조
            known = {c['cell_id'] for c in d['result'].get('cells', [])} | set(d['result'].get('not_found', []))
            return set(args.get('cell_ids', [])) <= known
        params = d.get('params') or {}
        return all(params.get(k) == v for k, v in args.items() if k != 'region' and k in params)

    def call(self, tool: str, args: dict) -> dict:
        hits = [(n, d) for n, d in self._fixtures if self._matches(d, tool, args)]
        if not hits:
            raise EngineError(f'예시 응답 없음: {tool} {args}')
        return _normalize_paths(copy.deepcopy(hits[0][1]))    # 여러 개면 파일 이름 순 첫 번째


def make_engine(kind: str):
    return {'live': LiveEngine, 'fixture': FixtureEngine}[kind]()


if __name__ == '__main__':
    # 예: python -m agent.engine_client classify --region 춘천 --engine live --save
    import argparse

    from agent.store import ResultStore

    ap = argparse.ArgumentParser(description='엔진 도구 하나를 불러 크기·evidence·caveats 를 본다')
    ap.add_argument('tool')
    ap.add_argument('--region', default='춘천')
    ap.add_argument('--engine', choices=['live', 'fixture'], default='fixture')
    ap.add_argument('--save', action='store_true', help='agent/out/runs/ 에 전체 결과 저장')
    a = ap.parse_args()

    res = make_engine(a.engine).call(a.tool, {'region': a.region})
    print(f'[{a.engine}] {a.tool} {a.region}: {len(json.dumps(res, ensure_ascii=False)):,}자')
    print('result 키:', list(res['result']))
    print('evidence:')
    for e in res['evidence']:
        print(f"  {e['metric']} = {e['value']}")
    print('caveats:')
    for c in res['caveats']:
        print('  -', c)
    print('params:', res['params'])
    if a.save:
        st = ResultStore()
        st.put(a.tool, {'region': a.region}, res)
        print('저장:', st.save())
