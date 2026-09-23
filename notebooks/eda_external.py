"""외부 데이터 EDA — 자원 접근성의 분포, 그리고 고령·유동인구와의 관계.

핵심 질문: "위험은 높은데 자원은 없는 격자"가 실제로 존재하는가?
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import numpy as np, pandas as pd
from scipy.stats import spearmanr
import config as C
from loaders import load_sk

pd.set_option('display.width', 220)
SEN = ['MAN_FLOW_POP_CNT_60GU', 'WMAN_FLOW_POP_CNT_60GU']
AGE = [f'{p}_FLOW_POP_CNT_{g}' for p in ['MAN', 'WMAN']
       for g in ['10G', '20G', '30G', '40G', '50G', '60GU']]


def sec(t): print(f"\n{'='*78}\n{t}\n{'='*78}")


def build():
    g = pd.read_parquet('preprocessed/grid_access.parquet')
    a = load_sk('flow_age_pop')
    a['total'] = a[AGE].sum(axis=1)
    a['senior'] = a[SEN].sum(axis=1)
    a['cell_id'] = (a.X_COORD.astype('int64').astype(str) + '_'
                    + a.Y_COORD.astype('int64').astype(str))
    s = (a.groupby('cell_id').agg(senior=('senior', 'sum'), total=('total', 'sum'))
           .assign(senior_ratio=lambda d: d.senior / d.total * 100).reset_index())
    return g.merge(s[['cell_id', 'senior_ratio']], on='cell_id', how='left')


def main():
    d = build()
    d['자원없음_300'] = d.opp_n300 == 0

    sec("1. 기회 자원 접근성 분포")
    print(d.groupby('region')[['opp_dist_min', 'opp_n300', 'opp_n500', 'opp_kinds_300']]
            .describe(percentiles=[.1, .25, .5, .75, .9]).T.round(1).to_string())

    sec("2. 자원 공백 격자 — 300m 내 기회 자원이 하나도 없는 곳")
    t = d.groupby('region').agg(
        격자수=('cell_id', 'size'),
        공백격자=('자원없음_300', 'sum'),
        공백비율=('자원없음_300', lambda x: round(x.mean() * 100, 1)))
    t['공백격자_유동인구'] = d[d.자원없음_300].groupby('region').flow_mean.sum().round(0)
    t['전체_유동인구'] = d.groupby('region').flow_mean.sum().round(0)
    t['공백_인구비중%'] = (t.공백격자_유동인구 / t.전체_유동인구 * 100).round(1)
    print(t.to_string())

    sec("3. 고령 비율과 자원 접근성의 관계 — 상관")
    for r, g in d.groupby('region'):
        print(f"\n  [{r}]  (Spearman, n={len(g):,})")
        for col, label in [('opp_n300', '300m내 자원 수'), ('opp_dist_min', '최근접 거리'),
                           ('n300_체육시설_공공', '300m내 공공체육'), ('n300_체육시설_민간', '300m내 민간체육')]:
            x = g.senior_ratio
            y = g[col]
            m = x.notna() & y.notna()
            rho, p = spearmanr(x[m], y[m])
            print(f"    고령비율 × {label:<14} rho={rho:+.3f}  p={p:.1e}")

    sec("4. 고령 비율 5분위별 평균 접근성")
    d['고령5분위'] = d.groupby('region').senior_ratio.transform(
        lambda s: pd.qcut(s, 5, labels=['Q1(낮음)', 'Q2', 'Q3', 'Q4', 'Q5(높음)']))
    t = (d.groupby(['region', '고령5분위'], observed=True)
           .agg(격자수=('cell_id', 'size'), 고령비율=('senior_ratio', 'mean'),
                유동인구=('flow_mean', 'median'),
                자원수_300m=('opp_n300', 'mean'), 최근접m=('opp_dist_min', 'median'),
                공공체육_300m=('n300_체육시설_공공', 'mean'),
                민간체육_300m=('n300_체육시설_민간', 'mean'),
                공백비율=('자원없음_300', lambda x: x.mean() * 100)).round(1))
    print(t.to_string())

    sec("5. 유동인구 규모를 통제하면? (규모 5분위 안에서 고령 상·하위 비교)")
    d['규모5분위'] = d.groupby('region').flow_mean.transform(
        lambda s: pd.qcut(s, 5, labels=[1, 2, 3, 4, 5]))
    rows = []
    for (r, q), g in d.groupby(['region', '규모5분위'], observed=True):
        hi = g[g.senior_ratio >= g.senior_ratio.quantile(.75)]
        lo = g[g.senior_ratio <= g.senior_ratio.quantile(.25)]
        rows.append({'region': r, '규모분위': q, '격자수': len(g),
                     '고령상위_자원수': round(hi.opp_n300.mean(), 2),
                     '고령하위_자원수': round(lo.opp_n300.mean(), 2),
                     '차이': round(hi.opp_n300.mean() - lo.opp_n300.mean(), 2)})
    print(pd.DataFrame(rows).to_string(index=False))

    sec("6. Resource Gap 후보 — 고령 상위 25% × 자원 하위 25%")
    out = []
    for r, g in d.groupby('region'):
        hs = g.senior_ratio >= g.senior_ratio.quantile(.75)
        lr = g.opp_n300 <= g.opp_n300.quantile(.25)
        gap = g[hs & lr]
        out.append({'region': r, '전체격자': len(g), 'Gap격자': len(gap),
                    '비율%': round(len(gap) / len(g) * 100, 1),
                    'Gap_고령비율': round(gap.senior_ratio.mean(), 1),
                    '전체_고령비율': round(g.senior_ratio.mean(), 1),
                    'Gap_유동인구합': round(gap.flow_mean.sum(), 0),
                    'Gap_최근접m중앙값': round(gap.opp_dist_min.median(), 0)})
    print(pd.DataFrame(out).to_string(index=False))

    C.TABLES.mkdir(parents=True, exist_ok=True)
    d.to_parquet('preprocessed/grid_access_senior.parquet', index=False)
    print(f"\n저장 → preprocessed/grid_access_senior.parquet ({len(d):,}행)")


if __name__ == '__main__':
    main()
