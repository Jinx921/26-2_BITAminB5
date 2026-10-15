"""지도·그래프(PNG)와 GeoJSON 출력. 프론트 지도 API는 GeoJSON(WGS84)을 쓰면 된다."""
from __future__ import annotations

import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Patch
from pyproj import Transformer

import config as C

# 한글 폰트: Windows / Mac / Linux 순서로 설치된 것 하나만 사용
_fonts = {f.name for f in matplotlib.font_manager.fontManager.ttflist}
plt.rcParams['font.family'] = next((f for f in ['Malgun Gothic', 'AppleGothic', 'NanumGothic'] if f in _fonts), 'sans-serif')
plt.rcParams['axes.unicode_minus'] = False
TO_WGS = Transformer.from_crs('EPSG:5179', 'EPSG:4326', always_xy=True)
HALF = 125
TYPE_COLOR = {'긴급방문형': '#C0392B', '연계형': '#7B68EE', '예방인프라형': '#F0A500', '관찰형': '#D5D8DC'}


def _save(fig, name):
    C.OUT.mkdir(parents=True, exist_ok=True)
    p = C.OUT / f'{name}.png'
    fig.savefig(p, dpi=130, bbox_inches='tight')
    plt.close(fig)
    return str(p.relative_to(C.ROOT))


def _base(ax, all_cells):
    ax.scatter(all_cells.x, all_cells.y, s=2, c='#EEEEEE', marker='s', linewidths=0)
    ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])


def _size(region):
    return 9 if region == '강남' else 3


def map_cells(all_cells, sel, col, region, title, name, cmap='Reds'):
    fig, ax = plt.subplots(figsize=(7, 7))
    _base(ax, all_cells)
    sc = ax.scatter(sel.x, sel.y, s=_size(region) * 3, c=sel[col], cmap=cmap, marker='s', vmin=3, vmax=6)
    fig.colorbar(sc, ax=ax, shrink=0.6, label='낮 활동 저하 개월 수')
    ax.set_title(title)
    return _save(fig, name)


def map_types(all_cells, u, region, title, name):
    fig, ax = plt.subplots(figsize=(7, 7))
    _base(ax, all_cells)
    for t in ['관찰형', '예방인프라형', '연계형', '긴급방문형']:
        s = u[u.type == t]
        ax.scatter(s.x, s.y, s=_size(region) * (4 if t in ('긴급방문형', '연계형') else 1.5),
                   c=TYPE_COLOR[t], marker='s', linewidths=0, label=f'{t} ({len(s)})')
    ax.legend(loc='lower left', fontsize=8)
    ax.set_title(title, fontsize=10)
    return _save(fig, name)


def map_sim(all_cells, dem, sites, radius, region, title, name):
    fig, ax = plt.subplots(figsize=(7, 7))
    _base(ax, all_cells)
    ax.scatter(dem.x, dem.y, s=_size(region) * 4, c=dem.covered.map({True: '#27AE60', False: '#C0392B'}), marker='s')
    for r in sites.itertuples():
        ax.add_patch(Circle((r.x, r.y), radius, fill=False, ec='#1F618D', lw=1.5))
        ax.plot(r.x, r.y, marker='*', ms=14, c='#1F618D')
    ax.legend(handles=[Patch(color='#27AE60', label='커버됨'), Patch(color='#C0392B', label='미커버'),
                       Patch(color='#1F618D', label='이동형 거점')], loc='lower left', fontsize=8)
    ax.set_title(title, fontsize=10)
    return _save(fig, name)


def map_change(all_cells, changed, region, title, name):
    cm = all_cells.set_index('cell_id').loc[changed.cell_id]
    fig, ax = plt.subplots(figsize=(7, 7))
    _base(ax, all_cells)
    ax.scatter(cm.x, cm.y, s=_size(region) * 5, c=[TYPE_COLOR.get(a.split('(')[0], '#555') for a in changed['after']],
               marker='s')
    ax.set_title(title, fontsize=10)
    return _save(fig, name)


def curve(rows, region, title, name):
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ks = [r['k'] for r in rows]
    ax.plot(ks, [r['covered_senior_share'] * 100 for r in rows], marker='o', label='60대+ 유동 커버 비율')
    ax.plot(ks, [r['covered_cells_share'] * 100 for r in rows], marker='s', ls='--', label='칸 커버 비율')
    ax.set_xlabel('이동형 거점 수 k'); ax.set_ylabel('%'); ax.set_ylim(0, 105); ax.set_xticks(ks)
    ax.legend(fontsize=8); ax.set_title(title, fontsize=10); ax.grid(alpha=.3)
    return _save(fig, name)


def geojson(df, props, name):
    feats = []
    for r in df.itertuples():
        ring = [TO_WGS.transform(r.x + dx, r.y + dy) for dx, dy in
                [(-HALF, -HALF), (HALF, -HALF), (HALF, HALF), (-HALF, HALF), (-HALF, -HALF)]]
        feats.append({'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [[list(p) for p in ring]]},
                      'properties': {k: (None if getattr(r, k) != getattr(r, k) else
                                         (getattr(r, k).item() if hasattr(getattr(r, k), 'item') else getattr(r, k)))
                                     for k in props}})
    C.OUT.mkdir(parents=True, exist_ok=True)
    p = C.OUT / f'{name}.geojson'
    p.write_text(json.dumps({'type': 'FeatureCollection', 'features': feats}, ensure_ascii=False), encoding='utf-8')
    return str(p.relative_to(C.ROOT))
