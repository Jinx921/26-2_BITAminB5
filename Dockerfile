# 백엔드(FastAPI + 에이전트 + 분석 엔진) 컨테이너. 저장소 루트에서 빌드한다.
#   docker build -t bitamin-backend .
#   docker run -p 8000:8000 -e ANTHROPIC_API_KEY=... -e BACKEND_JWT_SECRET=... bitamin-backend
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# scipy/lightgbm 류가 쓰는 OpenMP 런타임
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 먼저 (캐시 활용)
COPY backend/requirements.txt backend/requirements.txt
COPY agent/requirements.txt agent/requirements.txt
COPY engine/requirements.txt engine/requirements.txt
RUN pip install -r backend/requirements.txt

# 코드와 엔진 데이터 (data/ 원천 파일은 .dockerignore 로 제외)
COPY backend backend
COPY agent agent
COPY engine engine
COPY preprocessed preprocessed
COPY outputs outputs

# SQLite 파일 위치. 호스팅에서 볼륨을 /app/backend/data 에 붙이면 재배포 후에도 유지된다
RUN mkdir -p backend/data
ENV BACKEND_DB_PATH=/app/backend/data/app.db \
    BACKEND_ENVIRONMENT=production \
    PORT=8000

EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
