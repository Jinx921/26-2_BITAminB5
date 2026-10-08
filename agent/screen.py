"""화면 조각: 에이전트가 최종으로 내보내는 JSON.

display  프론트가 그리는 부분. 결론·설명(문단 목록)·확인할 점·신뢰도·지도 점
internal 백엔드가 로그로 저장하는 부분. 화면에 그리지 않는다
         (숫자 출처, 검증 결과, 신뢰도 근거, 엔진 caveat 원문, 도구 호출 순서)

검증에 끝내 실패하면 검증 안 된 문장은 보여주지 않고, 모드별 고정 안내 문구와 지도만 보여준다.
"""
from __future__ import annotations

import re

from agent.verifier import Context, VerifyResult

# 검증에 실패했을 때 화면에 보이는 안내 (모드마다 지도가 보여주는 것이 다르다)
FALLBACK_TEXT = {
    'admin': ('이 질문에 대한 설명을 아직 정리하지 못했습니다. 우선 확인이 필요한 동네는 지도에 표시해 두었습니다. '
              '잠시 후 다시 요청해 주시면 설명을 새로 정리해 드리겠습니다.'),
    'citizen': ('지금은 자세한 안내를 준비하지 못했어요. 지도에서 가까운 시설을 먼저 확인해 보세요. '
                '잠시 후 다시 물어봐 주시면 자세히 알려 드릴게요.'),
}

# 시민 모드에서 Sonnet 을 부르기 전에 끝나는 경우의 안내
REGION_NAMES = {'강남': '서울 강남구', '춘천': '춘천시'}
CITIZEN_NOTICE = {
    'no_location': ('어느 동네 주변을 찾아볼까요? 지도에서 동네를 고르거나 주소를 입력해 주세요. '
                    '지금 계신 곳 주변을 찾으려면 위치 사용을 허용해 주세요.'),
    'out_of_area': ('지금은 ' + '와 '.join(REGION_NAMES.values()) + '에서만 안내하고 있어요. '
                    '이 두 지역 안의 동네를 골라 다시 찾아봐 주세요.'),
}
# 내부 기록에서 가리는 인자 (사용자 위치)
LOCATION_KEYS = ('lat', 'lon')

# 지도로 그릴 수 있는 결과: 도구 → (layer, 결과 안의 행 목록, {지도 점 필드: 결과 필드})
MAP_ROWS = {
    'classify': ('types', 'table',
                 {'id': 'cell_id', 'lat': 'lat', 'lon': 'lon', 'emd_name': 'emd_name', 'type': 'type', 'gap': 'gap_tag'}),
    'find_candidates': ('candidates', 'cells',
                        {'id': 'cell_id', 'lat': 'lat', 'lon': 'lon', 'emd_name': 'emd_name',
                         'months': 'persistent_months'}),
    'simulate_placement': ('sites', 'chosen_sites',
                           {'id': 'cell_id', 'lat': 'lat', 'lon': 'lon', 'emd_name': 'emd_name', 'covers': 'covers'}),
    'lookup_resources': ('facilities', 'within_radius',
                         {'id': 'fac_id', 'lat': 'lat', 'lon': 'lon', 'name': 'name', 'kind': 'kind', 'dist_m': 'dist_m'}),
}
# 지도 점을 강조하는 기준: 화면 문장에 이 필드 값(시설 이름 / 행정동 이름)이 나오면 강조
HIGHLIGHT_BY = {'facilities': 'name', 'types': 'emd_name', 'candidates': 'emd_name', 'sites': 'emd_name'}
# 어느 문장을 볼지: 관리자는 결론에 "어디부터"가 있고 설명에는 행정동 순위 전체가 나오므로 결론만 본다.
# 시민은 설명에서 소개한 시설까지 강조한다
HIGHLIGHT_FROM = {'admin': ('headline',), 'citizen': ('headline', 'details', 'caution')}
# map_ref 가 없거나 지도로 그릴 수 없을 때 고르는 순서
MAP_FALLBACK_ORDER = ('classify', 'find_candidates', 'simulate_placement', 'lookup_resources')


def _mentioned(values: set[str], text: str) -> set[str]:
    """문장에 나온 이름. 긴 이름부터 찾아 지워서, 짧은 이름이 긴 이름의 일부로 잘못 잡히지 않게 한다
    (예: '…소양동10'이 나왔을 때 '…소양동1'은 강조하지 않음)."""
    found = set()
    for v in sorted(values, key=len, reverse=True):
        if v and v in text:
            found.add(v)
            text = text.replace(v, ' ')
    return found


def _map(ctx: Context, map_ref: str | None, text: str = '') -> dict | None:
    st = ctx.store
    ref = map_ref if map_ref in st.items and st.get(map_ref).tool in MAP_ROWS else None
    if ref is None:
        for tool in MAP_FALLBACK_ORDER:
            hits = st.by_tool(tool)
            if hits:
                ref = hits[-1].ref
                break
    if ref is None:
        return None
    s = st.get(ref)
    layer, rows_key, fields = MAP_ROWS[s.tool]
    rows = s.data['result'].get(rows_key, [])
    points = [{k: r.get(src) for k, src in fields.items()} for r in rows]
    key = HIGHLIGHT_BY.get(layer)
    hit = _mentioned({p[key] for p in points if p.get(key)}, text) if key else set()
    for p in points:
        p['highlight'] = bool(key) and p.get(key) in hit          # 답변에서 언급한 곳 (프론트가 강조)
    return {'layer': layer, 'ref': ref, 'points': points, 'geojson': s.data.get('geojson')}


def _region(ctx: Context) -> str | None:
    regions = {s.data.get('region') for s in ctx.store.items.values()} - {None}
    return regions.pop() if len(regions) == 1 else None


def _trace_args(mode: str, args: dict) -> dict:
    if mode != 'citizen':
        return args
    return {k: ('(사용자 위치)' if k in LOCATION_KEYS else v) for k, v in args.items()}


def build_screen(question: str, mode: str, answer: dict | None, check: VerifyResult | None,
                 ctx: Context, attempts: int = 1, notice: str | None = None) -> dict:
    """답변·검증 결과로 화면 조각을 만든다. answer 가 없거나 검증 실패면 안내 문구 + 지도.
    notice 가 있으면(질문 전에 끝난 경우) 그 문구만 보여주고 지도·신뢰도는 없다."""
    if notice is not None:
        return {'mode': mode, 'question': question, 'region': None,
                'display': {'headline': notice, 'details': [], 'caution': '', 'confidence': None, 'map': None},
                'internal': {'verification': {'passed': False, 'attempts': 0, 'errors': [], 'warnings': []},
                             'confidence_basis': {}, 'citations': [], 'caveats': [], 'tool_trace': []}}
    ok = answer is not None and check is not None and check.passed
    grade = check.grade if check else '낮음'
    note = check.grade_note if check else ''
    if ok:
        display = {
            'headline': answer['headline'].strip(),
            'details': [p.strip() for p in re.split(r'\n+', answer['details']) if p.strip()],
            'caution': answer['caution'].strip(),
        }
    else:
        display = {'headline': FALLBACK_TEXT[mode], 'details': [], 'caution': ''}
    # 신뢰도는 분석 결과가 기준에 따라 흔들리는 정도라 관리자 화면에만 보인다
    display['confidence'] = {'label': grade, 'note': note} if mode == 'admin' else None
    parts = {'headline': [display['headline']], 'details': display['details'], 'caution': [display['caution']]}
    shown = ' '.join(t for f in HIGHLIGHT_FROM[mode] for t in parts[f]) if ok else ''
    display['map'] = _map(ctx, answer['map_ref'] if answer else None, shown)

    reflected = set(answer['caveats_reflected']) if answer else set()
    internal = {
        'verification': {'passed': ok, 'attempts': attempts,
                         'errors': check.errors if check else ['답변이 제출되지 않음'],
                         'warnings': check.warnings if check else []},
        'confidence_basis': check.grade_basis if check else {},
        'citations': answer['citations'] if ok else [],
        'caveats': [{'id': cid, 'text': text, 'reflected': cid in reflected} for text, cid in ctx.caveat_ids.items()],
        'tool_trace': [{'ref': s.ref, 'tool': s.tool, 'args': _trace_args(mode, s.args)}
                       for s in ctx.store.items.values()],
    }
    if answer is not None and not ok:
        internal['rejected_answer'] = answer          # 검증에 실패한 원래 답변 (디버깅용)
    return {'mode': mode, 'question': question, 'region': _region(ctx), 'display': display, 'internal': internal}


if __name__ == '__main__':
    # 예: python -m agent.screen agent/out/examples/3_Sonnet답변_춘천_검증전.json --engine live
    import argparse
    import json
    from pathlib import Path

    from agent.engine_client import make_engine
    from agent.verifier import build_context, verify

    ap = argparse.ArgumentParser(description='저장된 submit_answer 답변으로 화면 조각 JSON 을 만든다')
    ap.add_argument('answer')
    ap.add_argument('--region', default='춘천')
    ap.add_argument('--engine', choices=['live', 'fixture'], default='fixture')
    ap.add_argument('--question', default='춘천에서 어디부터 확인해야 해?')
    ap.add_argument('--mode', choices=['admin', 'citizen'], default='admin')
    a = ap.parse_args()

    ctx = build_context(make_engine(a.engine), a.region, a.question, mode=a.mode)
    ans = json.loads(Path(a.answer).read_text(encoding='utf-8'))
    print(json.dumps(build_screen(a.question, a.mode, ans, verify(ans, ctx), ctx), ensure_ascii=False, indent=1))
