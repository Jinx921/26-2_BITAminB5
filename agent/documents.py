"""문서 생성 (관리자 모드): 사업 제안서 · 현황 보고 · 주민 안내문.

Sonnet 이 필요한 도구를 부른 뒤 submit_document 로 목차별 본문을 제출하면, 답변과 같은 방식으로 검증한다
(숫자 출처, 금지 표현, 필수 한계, 분량). 통과하면 화면 조각의 display.document 와 Markdown 파일로 내보낸다.

- 제안서: 결재용 공문이라 '근거 데이터' 목차에서만 분석 기준값을 쓸 수 있다
- 현황 보고: 지난 보고와 비교할 기록이 아직 없어 현 시점 현황만 정리한다
- 주민 안내문: 주민이 읽으므로 시민 금지어를 적용하고, 모르는 정보는 [날짜] 같은 빈칸으로 남긴다
"""
from __future__ import annotations

SUBMIT_DOC = 'submit_document'

DOC_SPECS = {
    'proposal': {
        'name': '사업 제안서', 'audience': 'admin',
        'sections': ('추진 배경', '대상 지역', '근거 데이터', '운영안', '기대 효과', '한계와 확인 사항'),
        'min_section': 100, 'params_in': ('근거 데이터',), 'needs_data': True,
    },
    'report': {
        'name': '현황 보고', 'audience': 'admin',
        'sections': ('현황 요약', '우선 확인 지역', '현장 확인이 필요한 동네', '다음 조치'),
        'min_section': 100, 'params_in': (), 'needs_data': True,
    },
    'notice': {
        'name': '주민 안내문', 'audience': 'citizen',
        'sections': ('방송 문구', '문자 문구', '게시물 문구'),
        'min_section': 0, 'max_chars': {'문자 문구': 90}, 'params_in': (), 'needs_data': False,
    },
}
PLACEHOLDERS = ('[날짜]', '[시간]', '[장소]', '[연락처]', '[담당자]')


def doc_fields(doc: dict) -> dict[str, str]:
    """검증용: 문서를 '필드 이름 → 문장'으로 펼친다 (제목 + 목차별 본문)."""
    out = {'title': doc['title']}
    for s in doc['sections']:
        out[s['heading']] = s['body']
    return out


def to_markdown(doc: dict) -> str:
    spec = DOC_SPECS[doc['doc_type']]
    lines = [f"# {doc['title']}", '', f"*{spec['name']} 초안 · 담당자 검토 후 사용*", '']
    for s in doc['sections']:
        lines += [f"## {s['heading']}", '', s['body'].strip(), '']
    return '\n'.join(lines)
