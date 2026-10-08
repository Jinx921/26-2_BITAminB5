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
        if d['params']:
            lines.append('params (인용 가능): ' + ', '.join(f'{k}={_fmt(v)}' for k, v in d['params'].items()))
            citable.update({f'params.{k}': v for k, v in d['params'].items()})

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
