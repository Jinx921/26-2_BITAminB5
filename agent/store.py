"""엔진 전체 결과 보관소.

Sonnet 에는 요약만 넘기고, 전체 결과는 여기 둔다. 각 결과에 ref("r1", "r2", ...)를 붙여
화면 조각(지도·표)이 ref 로 원본을 가리키고, 검증 단계가 ref 로 evidence·params 를 다시 찾는다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

RUNS_DIR = Path(__file__).resolve().parent / 'out' / 'runs'


@dataclass
class StoredResult:
    ref: str
    tool: str
    args: dict
    data: dict          # 엔진 응답 전체


@dataclass
class ResultStore:
    items: dict[str, StoredResult] = field(default_factory=dict)

    def put(self, tool: str, args: dict, data: dict) -> str:
        ref = f'r{len(self.items) + 1}'
        self.items[ref] = StoredResult(ref, tool, dict(args), data)
        return ref

    def get(self, ref: str) -> StoredResult:
        return self.items[ref]

    def by_tool(self, tool: str) -> list[StoredResult]:
        return [s for s in self.items.values() if s.tool == tool]

    def save(self, run_dir: Path | None = None) -> Path:
        """agent/out/runs/ 에 결과별 JSON 과 목록(index.json)을 쓴다.
        이전 실행 결과(r*_*, index.json)는 지우고 쓴다 (이번 실행 결과와 섞이지 않게)."""
        run_dir = Path(run_dir or RUNS_DIR)
        run_dir.mkdir(parents=True, exist_ok=True)
        for old in [*run_dir.glob('r[0-9]*_*'), run_dir / 'index.json']:
            if old.is_file():
                old.unlink()
        index = []
        for s in self.items.values():
            name = f'{s.ref}_{s.tool}.json'
            (run_dir / name).write_text(json.dumps(s.data, ensure_ascii=False, indent=1), encoding='utf-8')
            index.append({'ref': s.ref, 'tool': s.tool, 'args': s.args, 'file': name})
        (run_dir / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding='utf-8')
        return run_dir
