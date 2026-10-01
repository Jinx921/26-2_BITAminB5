"""모든 도구를 두 지역에서 한 번씩 돌려 예시 JSON·그림을 out/ 에 만든다.  python run_demo.py"""
import time

import core
import tool_schemas
from config import OUT

CALLS = [
    ('find_candidates', {}),
    ('classify', {}),
    ('simulate_placement', {'k': 3, 'radius_m': 1000}),
    ('simulate_placement', {'k': 3, 'radius_m': 3000}),
    ('robustness', {}),
    ('region_context', {}),
]

for region in ('강남', '춘천'):
    for name, kw in CALLS:
        t = time.time()
        r = core.TOOLS[name](region, **kw)
        tag = '_'.join(f'{k}{v}' for k, v in kw.items())
        core.dump(r, OUT / 'json' / f'{name}_{region}{"_" + tag if tag else ""}.json')
        print(f'{region:3} {name:20} {tag:18} {time.time() - t:5.1f}s  evidence {len(r["evidence"])}')

core.dump(core.lookup_resources('춘천', lat=37.8813, lon=127.7298), OUT / 'json' / 'lookup_resources_춘천_시청부근.json')
core.dump(core.check_residential(['3853_7769', '3851_7778']), OUT / 'json' / 'check_residential_예시.json')
core.dump(core.facility_change('춘천', remove_ids=['CC_00225']), OUT / 'json' / 'facility_change_춘천_지내2리경로당제거.json')
tool_schemas.SCHEMAS and core.dump(tool_schemas.SCHEMAS, OUT / 'tool_schemas.json')
print('완료 -> out/json, out/*.png, out/*.geojson, out/tool_schemas.json')
