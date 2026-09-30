"""외부 데이터 EDA — 자원 접근성과 고령·유동인구의 관계

격자 단위는 팀 표준 250m(`preprocessed/flow_cell.parquet`)를 따른다.
세 층위로 나눠 본다.
  ① 전체 250m 격자      — 복지시설 접근성 분석과 동일 모집단
  ② 야간비중 기준 통과   — 거주셀 조건 (a)만 적용한 근사치
  ③ 활동위축 후보셀 257개 — 고령 상위 25% + 이탈 지속 (srh_07)
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import numpy as np, pandas as pd
from scipy.stats import spearmanr
import config as C

pd.set_option('display.width', 220)
NIGHT_THR = {'강남': 0.07, '춘천': 0.03}      # 거주셀 조건 (a)


def sec(t): print(f"\n{'='*78}\n{t}\n{'='*78}")


def main():
    d = pd.read_parquet('preprocessed/grid_access.parquet')
    d['공백'] = d.opp_n300 == 0
    d['야간통과'] = d.apply(lambda r: r.night_share >= NIGHT_THR[r.region], axis=1)
    if 'is_candidate' not in d:
        d['is_candidate'] = False

    sec("0. 층위별 격자 수")
    t = d.groupby('region').agg(전체=('cell_id', 'size'),
                                야간통과=('야간통과', 'sum'),
                                후보셀=('is_candidate', 'sum'))
    print(t.to_string())
    print("  ※ 거주셀(야간 AND 주택) 최종 정의는 강남 625 / 춘천 1,952.")
    print("     주택 조건은 SGIS 데이터가 필요해 여기서는 야간 조건만 적용한 근사치다.")

    sec("1. 기회 자원 접근성 분포 (전체 250m 격자)")
    print(d.groupby('region')[['opp_dist_min', 'opp_n300', 'opp_n500', 'opp_kinds_300']]
            .describe(percentiles=[.25, .5, .75, .9]).T.round(1).to_string())

    sec("2. 자원 공백 격자 — 층위별")
    rows = []
    for lab, sub in [('전체 250m', d), ('야간통과', d[d.야간통과]), ('활동위축 후보셀', d[d.is_candidate])]:
        for reg, g in sub.groupby('region'):
            rows.append({'층위': lab, 'region': reg, '격자수': len(g),
                         '공백격자': int(g.공백.sum()),
                         '공백비율%': round(g.공백.mean() * 100, 1),
                         '최근접m_중앙값': round(g.opp_dist_min.median(), 0)})
    print(pd.DataFrame(rows).to_string(index=False))

    sec("3. 고령 비율 × 자원 접근성 상관 (Spearman)")
    for lab, sub in [('전체 250m', d), ('야간통과', d[d.야간통과])]:
        print(f"\n[{lab}]")
        for reg, g in sub.groupby('region'):
            line = [f"  {reg} (n={len(g):,})"]
            for col, nm in [('opp_n300', '통합자원'), ('n300_체육시설_공공', '공공체육'),
                            ('n300_체육시설_민간', '민간체육')]:
                m = g.senior_ratio.notna() & g[col].notna()
                rho, p = spearmanr(g.senior_ratio[m], g[col][m])
                line.append(f"{nm} {rho:+.3f}{'' if p < .01 else '(ns)'}")
            print("   ".join(line))

    sec("4. 유동인구 규모 × 자원 접근성 — 공공/민간 배치 논리")
    for reg, g in d.groupby('region'):
        line = [f"  {reg}"]
        for col, nm in [('n300_체육시설_공공', '공공체육'), ('n300_체육시설_민간', '민간체육')]:
            m = g.flow_mean.notna() & g[col].notna()
            rho, p = spearmanr(g.flow_mean[m], g[col][m])
            line.append(f"{nm} {rho:+.3f}{'' if p < .01 else '(ns)'}")
        print("   ".join(line))

    sec("5. 고령 5분위별 자원 접근성 (야간통과 격자)")
    s = d[d.야간통과].copy()
    s['고령5분위'] = s.groupby('region').senior_ratio.transform(
        lambda x: pd.qcut(x, 5, labels=['Q1(낮음)', 'Q2', 'Q3', 'Q4', 'Q5(높음)'], duplicates='drop'))
    print(s.groupby(['region', '고령5분위'], observed=True)
           .agg(격자수=('cell_id', 'size'), 고령비율=('senior_ratio', 'mean'),
                자원수_300m=('opp_n300', 'mean'),
                공공체육_300m=('n300_체육시설_공공', 'mean'),
                민간체육_300m=('n300_체육시설_민간', 'mean'),
                공백비율=('공백', lambda x: x.mean() * 100)).round(2).to_string())

    sec("6. 활동위축 후보셀은 자원도 부족한가")
    rows = []
    for reg, g in d.groupby('region'):
        cand, non = g[g.is_candidate], g[~g.is_candidate & g.야간통과]
        rows.append({'region': reg, '후보셀': len(cand), '비교군(야간통과 비후보)': len(non),
                     '후보_공백비율%': round(cand.공백.mean() * 100, 1),
                     '비후보_공백비율%': round(non.공백.mean() * 100, 1),
                     '후보_최근접m': round(cand.opp_dist_min.median(), 0),
                     '비후보_최근접m': round(non.opp_dist_min.median(), 0),
                     '후보_고령비율': round(cand.senior_ratio.mean(), 1)})
    print(pd.DataFrame(rows).to_string(index=False))
    print("\n  → 활동위축 후보셀이 자원 공백까지 겹치는지 확인. 겹치면 우선 지원 대상.")

    d.to_parquet('preprocessed/grid_access_senior.parquet', index=False)
    print(f"\n저장 → preprocessed/grid_access_senior.parquet ({len(d):,}행)")


if __name__ == '__main__':
    main()
