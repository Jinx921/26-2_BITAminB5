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
# map_ref 가 없거나 지도로 그릴 수 없을 때 고르는 순서
MAP_FALLBACK_ORDER = ('classify', 'find_candidates', 'simulate_placement', 'lookup_resources')


def _map(ctx: Context, map_ref: str | None) -> dict | None:
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
    return {'layer': layer, 'ref': ref,
            'points': [{k: r.get(src) for k, src in fields.items()} for r in rows],
            'geojson': s.data.get('geojson')}


def _region(ctx: Context) -> str | None:
    regions = {s.data.get('region') for s in ctx.store.items.values()} - {None}
    return regions.pop() if len(regions) == 1 else None


def build_screen(question: str, mode: str, answer: dict | None, check: VerifyResult | None,
                 ctx: Context, attempts: int = 1) -> dict:
    """답변·검증 결과로 화면 조각을 만든다. answer 가 없거나 검증 실패면 안내 문구 + 지도."""
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
    display['confidence'] = {'label': grade, 'note': note}
    display['map'] = _map(ctx, answer['map_ref'] if answer else None)

    reflected = set(answer['caveats_reflected']) if answer else set()
    internal = {
        'verification': {'passed': ok, 'attempts': attempts,
                         'errors': check.errors if check else ['답변이 제출되지 않음'],
                         'warnings': check.warnings if check else []},
        'confidence_basis': check.grade_basis if check else {},
        'citations': answer['citations'] if ok else [],
        'caveats': [{'id': cid, 'text': text, 'reflected': cid in reflected} for text, cid in ctx.caveat_ids.items()],
        'tool_trace': [{'ref': s.ref, 'tool': s.tool, 'args': s.args} for s in ctx.store.items.values()],
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
