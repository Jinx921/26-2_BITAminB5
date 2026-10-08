"""엔진 결과 요약 (Sonnet 에게 넘기는 tool_result 본문).

엔진 전체 결과는 store 에 두고, Sonnet 에는 다음만 넘긴다.
- evidence, params: 인용 가능한 숫자. 답변에 쓸 수 있는 숫자는 이 둘뿐이다
- 핵심 값: 도구별로 답변에 필요한 정보. 숫자는 넣지 않는다 (행정동 이름·순서 등)
- caveats: 번호(c1, c2, ...)를 붙여 넘기고, 앞 결과에 이미 나온 문장은 번호만 적는다

칸 목록·표·지도 데이터·전체 조합 표는 넘기지 않는다 (원본은 ref 로 store 에 있다).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from agent.store import StoredResult


def _fmt(v) -> str:
    return 'true' if v is True else 'false' if v is False else str(v)


def _ranked(counts: dict[str, int]) -> list[str]:
    """값이 큰 순서의 이름 (0 은 뺀다). 숫자 대신 순서만 넘기기 위해 쓴다."""
    return [k for k, v in sorted(counts.items(), key=lambda kv: -kv[1]) if v]


@dataclass
class Digest:
    text: str
    citable: dict[str, object]      # 인용 가능한 숫자: evidence metric → 값, params.<이름> → 값


@dataclass
class Digester:
    """한 질문 안에서 여러 도구 결과를 차례로 요약한다 (caveat 번호를 질문 단위로 공유)."""
    caveat_ids: dict[str, str] = field(default_factory=dict)   # 문장 → c 번호
    hidden_params: tuple = ()                                   # Sonnet 에 넘기지 않을 params (시민 모드: 찾을 위치 좌표)

    def __call__(self, s: StoredResult) -> Digest:
        d = s.data
        res = d['result']
        lines = [f"[{s.ref}] {d['tool']} · {d['region'] or '-'}"]
        citable: dict[str, object] = {}
        if 'error' in res or 'message' in res:
            lines.append(f"결과: {res.get('error') or res.get('message')}")
            return Digest('\n'.join(lines), citable)

        lines.append('evidence (인용 가능):')
        for e in d['evidence']:
            lines.append(f"  {e['metric']} = {_fmt(e['value'])}")
            citable[e['metric']] = e['value']
        params = {k: v for k, v in d['params'].items() if k not in self.hidden_params and v is not None}
        if params:
            lines.append('params (인용 가능): ' + ', '.join(f'{k}={_fmt(v)}' for k, v in params.items()))
            citable.update({f'params.{k}': v for k, v in params.items()})

        core = getattr(self, f"_core_{d['tool']}", self._core_default)(res)
        if core:
            lines.append('핵심 값 (숫자 없음, 설명용):')
            lines += [f'  {x}' for x in core]

        lines += self._caveats(d['caveats'])
        lines.append(f'원본: {s.ref} (칸 목록·표·지도 데이터는 화면이 원본에서 그린다)')
        return Digest('\n'.join(lines), citable)

    def _caveats(self, caveats: list[str]) -> list[str]:
        new, seen = [], []
        for c in caveats:
            if c in self.caveat_ids:
                seen.append(self.caveat_ids[c])
            else:
                cid = self.caveat_ids[c] = f'c{len(self.caveat_ids) + 1}'
                new.append(f'  {cid}: {c}')
        out = ['caveats:'] + new
        if seen:
            out.append(f"  (앞 결과와 같은 caveat: {', '.join(seen)})")
        return out

    # ------------------------------------------------------------ 도구별 핵심 값
    def _core_default(self, res: dict) -> list[str]:
        return [f"result 항목: {', '.join(res)}"]

    def _core_find_candidates(self, res: dict) -> list[str]:
        return ['후보가 많은 행정동 순: ' + ' > '.join(_ranked(res['by_emd'])),
                '주거건물 없어 뺀 이유: ' + ', '.join(_ranked(res['dropped_status']))]

    def _core_classify(self, res: dict) -> list[str]:
        layer = ' / '.join(f"{name}: {'·'.join(types)}" for name, types in res['layers'].items())
        acts = sorted(res['type_actions'].items(), key=lambda kv: kv[1]['priority'])
        lines = [f'층: {layer}',
                 '유형별 조치 (우선순위 순): ' + ' > '.join(f"{t}({a['action']})" for t, a in acts)]
        for t in ('긴급방문형', '연계형'):
            counts = {e: v.get(t, 0) for e, v in res['by_emd_withdrawn'].items()}
            lines.append(f'{t}이 많은 행정동 순: ' + ' > '.join(_ranked(counts)))
        # 칸 단위 목록(table)은 넘기지 않는다: 행정동 순서와 다른 기준으로 정렬돼 결론이 헷갈리고,
        # 칸 위치는 화면 지도가 원본에서 그린다
        return lines

    def _core_lookup_resources(self, res: dict) -> list[str]:
        # 시설 이름·주소는 결과에 나온 그대로 넘긴다 (거리는 evidence 에 있다)
        def row(r):
            return f"  {r['kind']}: {r['name']} / {r.get('addr') or '주소 정보 없음'}"
        lines = ['종류별 가장 가까운 시설 (거리는 evidence 의 nearest_종류_m):']
        lines += [row(r) for r in res.get('nearest_by_kind', [])]
        near = res.get('within_radius', [])
        if near:
            lines.append('반경 안 시설 (가까운 순, 거리는 가장 가까운 시설만 evidence 에 있다):')
            lines += [row(r) for r in near]
        lines.append('시설 이름·주소는 이 표기 그대로 쓴다')
        return lines

    def _core_simulate_placement(self, res: dict) -> list[str]:
        sites = [s['emd_name'] for s in res.get('chosen_sites', [])]
        return ['고른 거점 위치 (행정동, 덮는 칸이 많은 순): ' + ' > '.join(sites),
                '배치 후 대상 칸의 유형: ' + ', '.join(res.get('type_after', {})),
                '거점 수별 덮는 비율은 evidence 의 covered_senior_share_k1~k5 (60대 이상 유동 기준)',
                '거점 위치는 행정동 이름으로 말한다']

    def _core_facility_change(self, res: dict) -> list[str]:
        removed = [f"{r['name']}({r['kind']})" for r in res.get('removed', [])]
        added = [p.get('name', '신규 시설') for p in res.get('added', [])]
        moves = [f'{a} → {b}' for a, t in res.get('transitions', {}).items() for b in t if a != b]
        emd = {}
        for c in res.get('changed_cells', []):
            emd[c['emd_name']] = emd.get(c['emd_name'], 0) + 1
        lines = []
        if removed:
            lines.append('뺀 시설: ' + ', '.join(removed))
        if added:
            lines.append('더한 시설: ' + ', '.join(added))
        if res.get('not_found'):
            lines.append('찾지 못한 시설 ID (반영 안 됨): ' + ', '.join(res['not_found']))
        lines.append('유형이 바뀌는 방향: ' + (', '.join(moves) or '없음'))
        if emd:
            lines.append('유형이 바뀌는 칸이 많은 행정동 순: ' + ' > '.join(_ranked(emd)))
        return lines

    def _core_region_context(self, res: dict) -> list[str]:
        pct = res.get('senior60_card_time_pct', {})
        order = sorted(pct, key=pct.get, reverse=True)
        from agent.agent_tools import slot_label
        return [f"도시 해석 관점: {res.get('lens', '')}",
                '60대 이상 결제가 많은 시간대 순: ' + ' > '.join(slot_label(k) for k in order),
                '시간대는 이 표기 그대로 쓴다. 칸 단위 판단에는 쓰지 않는다']

    def _core_field_check(self, res: dict) -> list[str]:
        lines = ['확인 수준: 꼭 확인 / 확인 필요 (안정한 동네는 목록에서 뺐다)',
                 '확인할 동네가 많은 행정동 순: ' + ' > '.join(_ranked(res.get('by_emd', {}))),
                 '흔들리는 이유가 많은 순: ' + ' > '.join(_ranked(res.get('reason_counts', {}))),
                 '동네별 확인 질문과 방문 순서는 화면 목록이 원본에서 보여준다']
        return lines

    def _core_compare_interventions(self, res: dict) -> list[str]:
        opts = {o['key']: o for o in res.get('options', [])}
        order = sorted(opts.values(), key=lambda o: -o['resolved'])
        tie = len({o['resolved'] for o in order if o['key'] != 'baseline'}) == 1
        return ['비교한 안: ' + ' / '.join(o['name'] for o in opts.values()),
                '해소 수는 evidence 의 resolved_baseline·resolved_hub·resolved_mobile, 남는 수는 remaining_hub·remaining_mobile',
                ('경로당 거점과 이동형의 해소 수가 같다. 운영 방식의 차이(상설 거점 / 순회)를 쉬운 말로 설명한다'
                 if tie else '해소가 많은 순: ' + ' > '.join(o['name'] for o in order)),
                '이동형 거점 행정동: ' + ', '.join(opts['mobile']['where']),
                '경로당 거점 행정동: ' + ', '.join(opts['hub']['where']),
                '거점은 행정동 이름으로 말한다 (경로당 이름은 원천 데이터 표기라 알아보기 어려울 수 있다)']

    def _core_senior_industries(self, res: dict) -> list[str]:
        if 'senior_top' not in res:
            return [f"result 항목: {', '.join(res)}"]
        return ['60대 이상 비중이 높은 업종 순: ' + ' > '.join(x['industry'] for x in res['senior_top']),
                '지역 주민 이용 비율이 높은 업종 순: ' + ' > '.join(x['industry'] for x in res['local_top']),
                '둘 다 높은 생활 업종: ' + (', '.join(res['everyday_senior']) or '없음'),
                '쓰는 곳: 안내문을 둘 곳·함께 알릴 곳 제안 (가게 위치는 알 수 없으니 "이런 업종 근처"로만 말한다)',
                '업종 이름은 이 표기 그대로 쓴다']

    def _core_find_facility(self, res: dict) -> list[str]:
        rows = res.get('matches', [])
        if not rows:
            return ['찾은 시설 없음']
        lines = ['찾은 시설 (시설 ID: 이름 / 종류 / 주소):']
        lines += [f"  {r['fac_id']}: {r['name']} / {r['kind']} / {r.get('addr') or '주소 정보 없음'}" for r in rows]
        if len(rows) > 1:
            lines.append('같은 이름이 여러 곳이면 질문에 맞는 곳을 고르고, 애매하면 어느 곳 기준인지 답에서 밝힌다')
        return lines

    def _core_senior_hours(self, res: dict) -> list[str]:
        labels = res['slot_labels']
        order = sorted(res['senior60_card_time_pct'], key=res['senior60_card_time_pct'].get, reverse=True)
        return ['60대 이상 활동이 많은 시간대 순: ' + ' > '.join(labels[k] for k in order),
                '시간대는 이 표기 그대로 쓴다 (예: ' + labels[order[0]] + ')']

    def _core_robustness(self, res: dict) -> list[str]:
        # 기준값마다 긴급방문형 판정 겹침(jaccard)의 최저값 → 낮을수록 그 기준에 결과가 많이 흔들린다
        worst: dict[str, float] = {}
        for o in res['one_at_a_time']:
            j = o['urgent_jaccard']
            if j is not None:
                worst[o['param']] = min(j, worst.get(o['param'], j))
        order = sorted(worst, key=worst.get)
        return ['결과가 많이 흔들리는 기준 순 (긴급방문형 판정 겹침이 낮은 순): ' + ' > '.join(order)]


def digest_all(items: list[StoredResult]) -> list[Digest]:
    dg = Digester()
    return [dg(s) for s in items]


if __name__ == '__main__':
    # 예: python -m agent.digest --region 춘천 --engine live
    import argparse
    import json

    from agent.engine_client import make_engine
    from agent.store import ResultStore

    ap = argparse.ArgumentParser(description='시나리오 도구 결과를 요약해 원본과 크기를 비교한다')
    ap.add_argument('--region', default='춘천')
    ap.add_argument('--engine', choices=['live', 'fixture'], default='fixture')
    ap.add_argument('--tools', nargs='+', default=['find_candidates', 'classify', 'robustness'])
    ap.add_argument('--save', action='store_true', help='agent/out/runs/ 에 원본 JSON 과 요약 텍스트 저장')
    a = ap.parse_args()

    eng, st = make_engine(a.engine), ResultStore()
    for t in a.tools:
        st.put(t, {'region': a.region}, eng.call(t, {'region': a.region}))
    items = list(st.items.values())
    digests = digest_all(items)
    total_raw = total_dig = 0
    for s, d in zip(items, digests):
        raw = len(json.dumps(s.data, ensure_ascii=False))
        total_raw, total_dig = total_raw + raw, total_dig + len(d.text)
        print(d.text)
        print(f'  → 원본 {raw:,}자 → 요약 {len(d.text):,}자, 인용 가능 숫자 {len(d.citable)}개\n')
    print(f'합계: 원본 {total_raw:,}자 → 요약 {total_dig:,}자 ({total_dig / total_raw:.1%})')
    if a.save:
        run = st.save()
        for s, d in zip(items, digests):     # 원본 r1_도구.json 옆에 요약 r1_도구.digest.txt
            (run / f'{s.ref}_{s.tool}.digest.txt').write_text(d.text + '\n', encoding='utf-8')
        print('저장:', run)
