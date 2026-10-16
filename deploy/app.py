"""단일 배포용 진입점: FastAPI 백엔드 + 프론트 정적 파일(frontend/dist)을 한 서버에서 서빙한다.

backend/ 코드는 건드리지 않고 감싸기만 한다. API 경로(/api, /health, /docs)는 백엔드가 그대로 받고,
그 외 경로는 React Router 가 처리하도록 index.html 을 돌려준다.

    uvicorn deploy.app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import os
from pathlib import Path

import logging
from contextlib import asynccontextmanager

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.main import app  # 백엔드 앱 그대로 (라우트·CORS·lifespan 포함)

log = logging.getLogger("deploy")


# ---- 시작 시 계정 만들기 (환경 변수로) ----
# 호스팅에는 대화형 seed_user 를 돌릴 셸이 마땅치 않으므로, SEED_ADMIN_EMAIL/PASSWORD,
# SEED_FIELD_EMAIL/PASSWORD, SEED_CITIZEN_EMAIL/PASSWORD 가 있으면 서버가 뜰 때 없는 계정만 만든다.
# 이미 있으면 건너뛴다. 시민은 화면에서도 가입할 수 있어 시연용으로만 쓴다.
def _seed_accounts() -> None:
    from backend.app.auth import password_hash

    database = app.state.database
    for role, prefix in (("admin", "SEED_ADMIN"), ("field_worker", "SEED_FIELD"), ("citizen", "SEED_CITIZEN")):
        email = (os.getenv(f"{prefix}_EMAIL") or "").strip().lower()
        password = os.getenv(f"{prefix}_PASSWORD") or ""
        if not email or not password:
            continue
        if len(password) < 12:
            log.warning("%s_PASSWORD 는 12자 이상이어야 합니다. 건너뜀", prefix)
            continue
        if database.get_user_by_email(email):
            continue
        database.create_user(email, password_hash.hash(password), role=role)
        log.info("seeded %s account: %s", role, email)


_backend_lifespan = app.router.lifespan_context


@asynccontextmanager
async def _lifespan(app_):
    async with _backend_lifespan(app_) as state:  # 백엔드 lifespan 먼저 (DB 초기화, 엔진·에이전트 준비)
        try:
            _seed_accounts()
        except Exception:  # 계정 생성 실패가 서버를 막지 않게
            log.exception("계정 시드 실패")
        yield state


app.router.lifespan_context = _lifespan

DIST = Path(os.getenv("FRONTEND_DIST", Path(__file__).resolve().parents[1] / "frontend" / "dist"))
INDEX = DIST / "index.html"
API_PREFIXES = ("api/", "health", "docs", "openapi.json", "redoc")

if DIST.is_dir():
    # 해시가 붙은 정적 자산과 GeoJSON 은 그대로 서빙
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")
    if (DIST / "geo").is_dir():
        app.mount("/geo", StaticFiles(directory=DIST / "geo"), name="geo")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        """API 가 아닌 모든 경로 → 실제 파일이 있으면 그 파일, 없으면 index.html (SPA 폴백)."""
        if full_path.startswith(API_PREFIXES):
            return FileResponse(INDEX, status_code=404)
        candidate = (DIST / full_path).resolve()
        if full_path and candidate.is_file() and str(candidate).startswith(str(DIST.resolve())):
            return FileResponse(candidate)
        return FileResponse(INDEX)
