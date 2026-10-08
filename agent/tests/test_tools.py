"""3단계: 도구 목록과 모드별 권한."""
import copy

import pytest

from agent.engine_client import LiveEngine
from agent.tools import (AGENT_SCHEMAS, LOCKED_ARGS, MODE_TOOLS, SUBMIT, SUBMIT_SCHEMA, _engine_schemas, is_allowed, strip_locked,
                         tools_for)

RISK_TOOLS = ('find_candidates', 'classify', 'check_residential', 'simulate_placement', 'robustness',
              'facility_change', 'region_context')        # 위험 판정·유형 수가 결과에 나오는 도구


def _names(mode):
    return [t['name'] for t in tools_for(mode)]


def test_citizen_has_no_risk_tools():
    names = _names('citizen')
    for t in RISK_TOOLS:
        assert t not in names
        assert not is_allowed('citizen', t)          # 목록뿐 아니라 실행 단계에서도 거절
    assert names == ['lookup_resources', 'senior_hours', SUBMIT]


def test_admin_has_all_engine_tools():
    names = _names('admin')
    engine = [s['name'] for s in _engine_schemas()]
    assert names[:len(engine)] == engine and names[-1] == SUBMIT
    assert set(names[len(engine):-1]) <= set(AGENT_SCHEMAS)                 # 그 사이는 에이전트 도구


def test_every_engine_tool_has_a_mode_decision():
    """엔진에 새 도구가 생기면 MODE_TOOLS 에서 어느 모드에 줄지 정해야 한다."""
    engine_tools = set(LiveEngine().tool_names) if _engine_data() else {s['name'] for s in _engine_schemas()}
    assert engine_tools == set(MODE_TOOLS['admin']) - set(AGENT_SCHEMAS)


def _engine_data():
    from agent.engine_client import ENGINE_DIR
    return (ENGINE_DIR / 'preprocessed' / 'cell_master.parquet').exists()


def test_locked_args_removed():
    tools = {t['name']: t for t in tools_for('admin')}
    for tool, args in LOCKED_ARGS.items():
        props = tools[tool]['input_schema']['properties']
        for a in args:
            assert a not in props
        assert 'region' in props and tools[tool]['input_schema']['required'] == ['region']


def test_engine_schemas_not_mutated():
    before = copy.deepcopy(_engine_schemas())
    tools_for('admin'), tools_for('citizen')
    assert _engine_schemas() == before
    assert 'persist_min' in {s['name']: s for s in before}['find_candidates']['input_schema']['properties']


def test_strip_locked():
    args, dropped = strip_locked('classify', {'region': '춘천', 'far_social_m': 1000})
    assert args == {'region': '춘천'} and dropped == ['far_social_m']
    assert strip_locked('robustness', {'region': '춘천'}) == ({'region': '춘천'}, [])


def test_unknown_mode():
    with pytest.raises(ValueError):
        tools_for('guest')
    assert not is_allowed('guest', 'lookup_resources')


def _check_strict(node):
    """strict 도구 규칙: 모든 object 는 additionalProperties=false 이고 모든 속성이 required."""
    if node.get('type') == 'object':
        assert node['additionalProperties'] is False
        assert set(node['required']) == set(node['properties'])
        for p in node['properties'].values():
            _check_strict(p)
    if node.get('type') == 'array':
        _check_strict(node['items'])


def test_submit_schema_strict():
    assert SUBMIT_SCHEMA['strict'] is True
    _check_strict(SUBMIT_SCHEMA['input_schema'])


def test_submit_schema_fields():
    """화면에 보이는 부분(결론·설명·확인할 점)과 내부 기록(caveat 반영·숫자 출처·지도)이 나뉘어 있다."""
    props = SUBMIT_SCHEMA['input_schema']['properties']
    assert {'headline', 'details', 'caution'} <= set(props)
    assert {'caveats_reflected', 'citations', 'map_ref'} <= set(props)
