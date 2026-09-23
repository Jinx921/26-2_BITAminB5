"""외부 데이터 선별 판정 — data/external/*.csv 를 넣고 실행한다.

  python3 notebooks/check_external.py

세 가지 기준으로 채택/제외를 판정한다.
  ① 강남·춘천 행 수      — 너무 적으면 격자 분석 불가
  ② 격자 커버리지 변별력  — 500m내 비율이 0%나 100%에 붙으면 구분력 없음
  ③ 좌표 중복            — 다른 유형과 같은 지점이면 통합 대상
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import numpy as np, pandas as pd
import config as C
from external import load_external, valid_cells, accessibility

pd.set_option('display.width', 220)
MIN_ROWS = 10        # ① 지역당 최소 시설 수
LO, HI = 5, 95       # ② 500m내 비율이 이 밖이면 변별력 없음


def verdict(r):
    cov = r['500m내_격자비율%']
    if r['시설수'] < MIN_ROWS:
        return f'제외 — 시설 {r["시설수"]}개뿐'
    if cov < LO:
        return f'제외 — 커버리지 {cov}%, 거의 모든 격자가 멀다'
    if cov > HI:
        return f'보조 — 커버리지 {cov}%, 거의 모든 격자가 가깝다 (변별력 없음)'
    return '채택'


def main():
    print(f"[1] data/external 읽기  ({C.EXTERNAL})")
    ext = load_external()

    print(f"\n[2] 지역별 시설 수")
    t = pd.crosstab(ext.kind, ext.region.fillna('대상외'))
    print(t.to_string())
    miss = [k for k in t.index if t.loc[k].get('강남', 0) == 0 or t.loc[k].get('춘천', 0) == 0]
    if miss:
        print(f"  ⚠ 한쪽 지역이 비어 있음 → 지역 비교 불가: {', '.join(miss)}")

    print(f"\n[3] 분석 대상 격자 (6개월 완전관측 + 일평균 30명 이상)")
    cells = valid_cells()
    print(cells.groupby('region').size().to_string())

    print(f"\n[4] 격자 접근성 — 채택 판정")
    acc = accessibility(ext, cells)
    if acc.empty:
        print("  대상 지역 시설이 없어 계산 불가")
        return
    acc['판정'] = acc.apply(verdict, axis=1)
    print(acc.sort_values(['region', '500m내_격자비율%'], ascending=[True, False]).to_string(index=False))

    print(f"\n[5] 좌표 중복 (같은 지점을 여러 유형이 가리키는 경우)")
    e = ext[ext.region.notna()].copy()
    e['pt'] = e.x.round(-1).astype(int).astype(str) + '_' + e.y.round(-1).astype(int).astype(str)
    dup = e.groupby('pt').kind.nunique()
    n = int((dup > 1).sum())
    print(f"  10m 이내에 2개 이상 유형이 겹치는 지점: {n:,}개")
    if n:
        pairs = (e[e.pt.isin(dup[dup > 1].index)]
                 .groupby('pt').kind.apply(lambda s: ' + '.join(sorted(set(s))))
                 .value_counts().head(8))
        print(pairs.to_string())

    C.TABLES.mkdir(parents=True, exist_ok=True)
    out = C.TABLES / 'ext_01_접근성_판정.csv'
    acc.to_csv(out, index=False, encoding='utf-8-sig')
    print(f"\n저장 → {out}")


if __name__ == '__main__':
    main()
