# 단일 배포 이미지: 프론트(Vite 빌드) + 백엔드(FastAPI + 에이전트 + 엔진)를 한 컨테이너에서 서빙한다.
#   docker build -t bitamin .
#   docker run -p 8000:8000 -e ANTHROPIC_API_KEY=... -e BACKEND_JWT_SECRET=... -e BACKEND_ALLOWED_ORIGINS=https://... bitamin

# ---- 1단계: 프론트 빌드 ----
FROM node:22-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
# 같은 서버에서 서빙하므로 API 주소는 상대 경로("")로, 목업은 끔
ENV VITE_USE_MOCK=false VITE_API_BASE_URL="" VITE_GEO_BASE_URL=/geo
RUN npm run build

# ---- 2단계: 백엔드 + 정적 파일 ----
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
COPY agent/requirements.txt agent/requirements.txt
COPY engine/requirements.txt engine/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend backend
COPY agent agent
COPY engine engine
COPY preprocessed preprocessed
COPY outputs outputs
COPY deploy deploy
COPY --from=frontend /fe/dist frontend/dist

# SQLite 위치. 호스팅 볼륨을 /app/backend/data 에 붙이면 재배포 후에도 유지된다
RUN mkdir -p backend/data
ENV BACKEND_DB_PATH=/app/backend/data/app.db BACKEND_ENVIRONMENT=production PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn deploy.app:app --host 0.0.0.0 --port ${PORT}"]
