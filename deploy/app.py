"""단일 배포용 진입점: FastAPI 백엔드 + 프론트 정적 파일(frontend/dist)을 한 서버에서 서빙한다.

backend/ 코드는 건드리지 않고 감싸기만 한다. API 경로(/api, /health, /docs)는 백엔드가 그대로 받고,
그 외 경로는 React Router 가 처리하도록 index.html 을 돌려준다.

    uvicorn deploy.app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.main import app  # 백엔드 앱 그대로 (라우트·CORS·lifespan 포함)

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
