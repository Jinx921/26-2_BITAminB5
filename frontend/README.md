# 프론트엔드 (frontend/)

사회적 고립 대응 AI 에이전트의 화면. 관리자 웹, 시민 웹(모바일 우선), 현장 모바일 세 가지를 한 앱에서 역할별 라우트로 제공한다.

## 실행

```bash
cd frontend
npm install
cp .env.example .env     # 처음 한 번. 기본값은 목업 모드
npm run dev              # http://localhost:5173 (포트 고정, 사용 중이면 실패)
```

| 명령 | 내용 |
| --- | --- |
| `npm run dev` | 개발 서버 (5173, strictPort) |
| `npm run build` | 타입 검사 후 `dist/` 빌드 |
| `npm run lint` | oxlint |
| `npm run preview` | 빌드 결과 미리보기 |

## 환경 변수 (`.env`, 커밋하지 않음)

| 변수 | 기본값 | 뜻 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | FastAPI 백엔드 주소 |
| `VITE_USE_MOCK` | `true` | `true`면 백엔드 없이 목업으로 전 화면 동작 |
| `VITE_GEO_BASE_URL` | `/geo` | 격자·시설 GeoJSON 위치. 백엔드가 정적 서빙을 시작하면 그 주소로 바꾼다 |

### 목업 모드 데모 계정

| 역할 | 이메일 | 비밀번호 |
| --- | --- | --- |
| 관리자 | `admin@demo.local` | `demo-admin-1234` |
| 시민 | `citizen@demo.local` | `demo-citizen-1234` |
| 현장 담당자 | `field@demo.local` | `demo-field-1234` |

로그인 화면의 버튼으로 바로 들어갈 수 있다. 목업 데이터(지원 요청·현장 기록)는 브라우저 localStorage 에 저장되므로 같은 브라우저의 관리자·시민·현장 화면이 공유한다.

### 실제 백엔드 연결

```bash
# 저장소 루트에서
source .venv/bin/activate
uvicorn backend.app.main:app --reload          # 8000번, CORS 는 localhost:5173 기본 허용
python -m backend.seed_user --role admin        # 관리자 계정
python -m backend.seed_user --role field_worker # 현장 담당자 계정
```

`.env`에서 `VITE_USE_MOCK=false` 로 바꾸고 개발 서버를 다시 띄운다. 시민 계정은 `/api/v1/auth/register` 로 만든다 (비밀번호 12자 이상).

## 폴더 구조

```
src/
  api/          client.ts (fetch·토큰·오류)  endpoints.ts (계약서 1:1)  mock/ (목업)  index.ts (스위치)
  auth/         AuthProvider, useAuth, RequireRole (역할 가드), roleHome
  types/        api.ts (docs/api-contract.md)  display.ts (에이전트 화면 조각)
  config.ts     환경 변수, 지역(강남·춘천) 중심·범위, 주민센터 전화 자리
  layouts/      AppShell (관리자 상단 메뉴 / 시민·현장 하단 탭), 역할별 레이아웃
  pages/        login, admin/, citizen/, field/
  components/ui 공통 버튼·카드·스피너·빈 상태·오류 상태
  lib/          TanStack Query 클라이언트
public/geo/     격자·시설 GeoJSON (engine/out 복사본, scripts/sync-geo.sh 로 갱신)
```

### 라우트와 권한

| 경로 | 역할 | 화면 |
| --- | --- | --- |
| `/login` | 공개 | 로그인 |
| `/admin`, `/admin/requests`, `/admin/field-list` | admin | 유형 지도·질문, 시민 요청, 현장 확인 목록 |
| `/citizen`, `/citizen/places`, `/citizen/schedule`, `/citizen/help/:facilityId` | citizen | 물어보기, 갈 곳, 이번 주, 함께 가기·이동 도움 |
| `/field`, `/field/cells/:cellId` | field_worker, admin | 확인 목록, 동네 확인 |

권한이 없는 경로로 가면 그 역할의 첫 화면으로 보내고, 로그인하지 않았으면 `/login` 으로 보낸다. 토큰은 sessionStorage 에만 두며 만료(1시간)되거나 401 을 받으면 로그아웃된다.

## 지킬 것 (agent/README.md 7절, engine/지도_규격.md)

- 질문 응답의 `display` 만 그린다. `internal` 은 받지도 그리지도 않는다.
- 시민 화면에 위험 판정·고립 유형·신뢰도·후보 격자를 노출하지 않는다.
- `cell_id`·`fac_id` 는 화면 글자로 보여주지 않고 조회 키로만 쓴다.
- `agent/`, `engine/` 폴더는 읽기만 하고 수정하지 않는다.

## 임시 처리 (백엔드 API 가 생기면 교체)

| 항목 | 지금 | 교체 지점 |
| --- | --- | --- |
| 현장 확인 목록 전달 | 목업: 공유 저장소 / 실제: 복사·내려받기 | `api/types.ts` 의 `publishFieldCheckList`, `fetchFieldCheckList` |
| 현장 판정 덮어쓰기(`has_residents=no` 숨김 등) | 프론트에서 로컬 계산 (2·3단계) | 예정: `map/applyFieldOverrides.ts` |
| GeoJSON 제공 | `public/geo/` 정적 복사본 | `VITE_GEO_BASE_URL` |
