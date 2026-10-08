"""터미널 실행: 질문 하나를 실제 Sonnet·엔진으로 끝까지 처리하고 화면에 보일 답과 내부 기록 요약을 출력한다.

예: python -m agent.run "춘천에서 어디부터 확인해야 해?"
    python -m agent.run "강남에서 어디부터 확인해야 해?" --engine live
결과 전체(screen.json, 엔진 원본)는 agent/out/runs/ 에 저장된다.
"""
from __future__ import annotations

import argparse
import textwrap
import time
from collections import Counter

from agent.engine_client import make_engine
from agent.orchestrator import Orchestrator, save_run


def _print_display(d: dict) -> None:
    print('\n' + '=' * 24 + ' 화면에 보이는 답 ' + '=' * 24)
    print('\n[결론]')
    print(textwrap.fill(d['headline'], 70))
    if d['details']:
        print('\n[설명]')
        for p in d['details']:
            print(textwrap.fill(p, 70) + '\n')
    if d['caution']:
        print('[확인할 점]')
        print(textwrap.fill(d['caution'], 70))
    c = d['confidence']
    if c:
        print(f"\n[신뢰도] {c['label']}" + (f"  {c['note']}" if c['note'] else ''))
    ch = d.get('chart')
    if ch:
        print(f"\n[차트] {ch['title']}")
        for i in ch['items']:
            print(f"  {i['label']:<12} {'■' * i['value'] if ch['total'] <= 60 else ''} {i['value']}{ch['unit']}")
    m = d['map']
    if m:
        kinds = Counter(p.get('type') for p in m['points'] if p.get('type'))
        print(f"[지도] {m['layer']} 점 {len(m['points'])}개" +
              (f" ({', '.join(f'{t} {n}' for t, n in kinds.items())})" if kinds else ''))
        hl = [p.get('name') or p.get('emd_name') for p in m['points'] if p.get('highlight')]
        if hl:
            print(f"       강조 {len(hl)}개: {', '.join(dict.fromkeys(hl))}")


def _print_internal(i: dict, seconds: float) -> None:
    print('\n' + '=' * 24 + ' 내부 기록 (화면에 안 보임) ' + '=' * 19)
    run, v = i['run'], i['verification']
    print('도구 호출:', ' → '.join(f"{t['ref']} {t['tool']}" for t in i['tool_trace']) or '없음')
    print(f"검증: {'통과' if v['passed'] else '실패'} (제출 {v['attempts']}회) · 끝난 이유: {run['end']}")
    for r in run['rejected']:
        print(f"  {r['attempt']}차 제출 실패 사유:")
        for e in r['errors']:
            print('    -', e)
    for e in v['errors']:
        print('  [오류]', e)
    for w in v['warnings']:
        print('  [경고]', w)
    print(f"반영한 한계: {', '.join(c['id'] for c in i['caveats'] if c['reflected']) or '없음'}"
          f" / 전체 {len(i['caveats'])}개")
    print(f"인용한 숫자: {', '.join(c['text'] for c in i['citations']) or '없음'}")
    tot_in = sum(c['input_tokens'] for c in run['calls'])
    tot_out = sum(c['output_tokens'] for c in run['calls'])
    tot_read = sum(c['cache_read_input_tokens'] for c in run['calls'])
    tot_write = sum(c['cache_creation_input_tokens'] for c in run['calls'])
    print(f"Sonnet 호출 {len(run['calls'])}회 · 입력: 일반 {tot_in:,} + 캐시 쓰기 {tot_write:,} + 캐시 읽기 {tot_read:,}"
          f" / 출력 {tot_out:,} 토큰"
          f" · {seconds:.0f}초 · {run['model']} effort={run['effort']}")


def main() -> None:
    ap = argparse.ArgumentParser(description='질문 하나를 실제 Sonnet 으로 처리한다')
    ap.add_argument('question')
    ap.add_argument('--mode', choices=['admin', 'citizen'], default='admin')
    ap.add_argument('--engine', choices=['live', 'fixture'], default='live')
    ap.add_argument('--lat', type=float, help='시민 모드: 찾을 위치의 위도 (앱이 넘겨주는 값)')
    ap.add_argument('--lon', type=float, help='시민 모드: 찾을 위치의 경도')
    a = ap.parse_args()
    location = {'lat': a.lat, 'lon': a.lon} if a.lat is not None and a.lon is not None else None

    t0 = time.time()
    screen, turn = Orchestrator(make_engine(a.engine), mode=a.mode).ask(a.question, location)
    seconds = time.time() - t0
    _print_display(screen['display'])
    _print_internal(screen['internal'], seconds)
    print('\n저장:', save_run(screen, turn) / 'screen.json')


if __name__ == '__main__':
    main()
