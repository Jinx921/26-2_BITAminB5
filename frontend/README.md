# 프론트엔드 (frontend/)

사회적 고립 대응 AI 에이전트(강남구·춘천시)의 화면. 관리자 웹, 시민 웹(모바일 우선), 현장 모바일 세 가지를 한 앱에서 역할별 라우트로 제공한다.
Vite + React 19 + TypeScript, React Router 7, TanStack Query 5, Tailwind CSS 4, react-leaflet(OpenStreetMap).

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
| `npm run typecheck` | `tsc -b` |
| `npm run lint` | oxlint |
| `npm run sync-geo` | `engine/out/*.geojson` → `public/geo/` 복사 (시설 지도는 `origin/hyunjun` 에서 추출) |

## 환경 변수 (`.env`, 커밋하지 않음)

| 변수 | 기본값 | 뜻 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | FastAPI 백엔드 주소 |
| `VITE_USE_MOCK` | `true` | `true`면 백엔드 없이 목업으로 전 화면 동작 |
| `VITE_GEO_BASE_URL` | `/geo` | 격자·시설 GeoJSON 위치. 백엔드가 정적 서빙을 시작하면 그 주소로 바꾼다 |

### 목업 모드 데모 계정

| 역할 | 이메일 | 비밀번호 |
| --- | --- | --- |
| 관리자 | `admin@example.com` | `demo-admin-1234` |
| 시민 | `citizen@example.com` | `demo-citizen-1234` |
| 현장 담당자 | `field@example.com` | `demo-field-1234` |

로그인 화면의 버튼으로 바로 들어갈 수 있다. 목업의 질문 응답은 `agent/out/examples` 의 화면조각 19개를 그대로 쓰고(키워드·지역·위치로 선택), 지원 요청·현장 기록·현장 확인 목록은 브라우저 localStorage 에 저장되어 같은 브라우저의 관리자·시민·현장 화면이 공유한다.

### 실제 백엔드 연결

백엔드는 Python 3.11 이상이 필요하다 (`logging.getLevelNamesMapping`). 루트 `.venv` 가 3.10 이면 3.11+ 로 가상환경을 새로 만든다.

```bash
# 저장소 루트에서
source .venv/bin/activate                       # Python 3.11+
python -m pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload          # 8000번, CORS 는 localhost:5173 기본 허용
python -m backend.seed_user --role admin        # 관리자 계정 (대화형)
python -m backend.seed_user --role field_worker # 현장 담당자 계정
```

`.env`에서 `VITE_USE_MOCK=false` 로 바꾸고 개발 서버를 다시 띄운다. 시민 계정은 로그인 화면 안내대로 `POST /api/v1/auth/register` 로 만든다(비밀번호 12자 이상). 질문 API 는 `agent/.env` 의 Anthropic 키가 있어야 실제 답을 돌려준다.

## 시연 시나리오 (목업 모드)

| 역할 | 흐름 |
| --- | --- |
| 관리자 ① | 로그인 → 지도와 질문 → "춘천에서 어디부터 확인해야 해?" → 결론·신뢰도, 언급된 행정동 칸이 지도에 강조 |
| 관리자 ② | "춘천 외곽에 거점 3곳을 둔다면 이동형이랑 경로당 거점 중 뭐가 나아?" → 막대그래프 + 거점 지도 |
| 관리자 ③ | "춘천 외곽 이동형 건강상담 사업 제안서 써줘" → 문서 조각 → `.md 내려받기` |
| 관리자 ④ | "춘천 현장 확인 목록 만들어 줘" → `이 목록을 현장 담당자에게 보내기` → 현장 확인 목록 화면 |
| 시민 | 위치 고르기(지도에서 춘천 시내 클릭) → "어머니 댁 근처에 다니실 만한 곳 있어요?" → 장소 카드 → `함께 갈 이웃 찾기` → 요청 보내기 → 관리자 "시민 요청" 탭에 대기 건으로 표시 |
| 현장 | 로그인 → 관리자가 보낸 목록 → 동네 선택 → 버튼 답변 + "지원 필요 여부" + 메모 → 저장 → 목록에 "저장됨". `has_residents = 아니오` 로 저장하면 관리자 지도에서 그 칸이 사라진다(임시 처리) |

## 폴더 구조

```
src/
  api/            client.ts (fetch·토큰·오류·Retry-After)  endpoints.ts (계약서 1:1)  types.ts (인터페이스)
                  mock/ (데모 계정, localStorage 저장소, fixtures/ 화면조각 19개, 키워드 매칭)  index.ts (스위치)
  auth/           AuthProvider, useAuth, RequireRole (역할 가드), roleHome
  types/          api.ts (docs/api-contract.md)  display.ts (에이전트 화면 조각)  geo.ts (GeoJSON properties)
  config.ts       환경 변수, 지역(강남·춘천) 중심·bbox, 주민센터 전화 자리
  fragments/      toFragments (display → 조각 배열, 모드별 순서)  registry  FragmentRenderer  components/ 조각 8종
  map/            BaseMap(OSM)  GridLayer(격자 색칠)  PointsLayer(레이어별 점)  markers  colors  useGeoLayer  applyFieldOverrides(임시)
  features/       citizen/ (세션, 접근성, 지오코딩, 공유, 일정)  admin/ (현장 목록 변환)  field/ (체크리스트 키, 저장 표시)
  components/     ui/ 공통, QuestionBox, map/ (지역 탭·범례), citizen/ (위치 고르기·장소 카드·접근성 바)
  layouts/        AppShell (관리자 상단 메뉴 / 시민·현장 하단 탭), 역할별 레이아웃
  pages/          login, admin/, citizen/, field/
  lib/            queryClient, useAskQuestion, download, geoIndex (ID → 이름)
public/geo/       격자·시설 GeoJSON (engine/out 복사본, WGS84)
scripts/          sync-geo.sh
```

### 라우트와 권한

| 경로 | 역할 | 화면 |
| --- | --- | --- |
| `/login` | 공개 | 로그인 |
| `/admin` | admin | 동네 유형 지도(GeoJSON 전체 색칠) + 질문창 + 응답 조각, 현장 목록 보내기 |
| `/admin/requests` | admin | 시민 요청 목록(승인·반려·완료), 수요 신호·현장 피드백 집계 |
| `/admin/field-list` | admin | 현장 확인 목록 생성·보내기·복사·내려받기 |
| `/citizen` | citizen | 위치 고르기, 질문(음성), 답변, 장소 카드, 공유·전화 |
| `/citizen/places` | citizen | 시설 지도 + 카드(길찾기·일정 저장·함께 가기·이동 도움) |
| `/citizen/schedule` | citizen | 이번 주 일정(.ics) |
| `/citizen/help/:facilityId` | citizen | 함께 가기 / 이동 도움 요청 폼 |
| `/field` | field_worker, admin | 받은 확인 목록, .json 불러오기 |
| `/field/cells/:cellId` | field_worker, admin | 동네별 버튼 답변·메모·저장, 이전 기록 |

권한이 없는 경로로 가면 그 역할의 첫 화면으로 보내고, 로그인하지 않았으면 `/login` 으로 보낸다. 토큰은 sessionStorage 에만 두며 만료(1시간)되거나 401 을 받으면 로그아웃된다.

## 화면 조각 렌더러

백엔드 `POST /api/v1/questions` 는 `display` 객체 하나를 돌려준다(`headline`, `details[]`, `caution`, `confidence`, `map`, `chart`, `document`).
`fragments/toFragments.ts` 가 이 객체를 모드별 순서의 조각 배열로 바꾸고, `registry.ts` 에 type 별로 등록된 컴포넌트가 순서대로 그린다.

- 관리자 순서: headline → confidence → map → chart → details → caution → document
- 시민 순서: headline → map(시설 레이어만) → details → caution. confidence·chart 는 그리지 않는다
- null·빈 값은 건너뛰고, 계약서에 없는 키는 관리자 화면에서 `unknown` 조각으로 접어서 보여준다
- 조각마다 에러 바운더리가 있어 하나가 깨져도 나머지는 보인다

새 조각 종류를 추가할 때는 `types/display.ts` 에 타입을 더하고 `fragments/index.ts` 에서 `registerFragment` 한다.

## 지도

- 좌표계는 WGS84(경도, 위도)라 변환 없이 Leaflet 에 올린다. 250m 격자는 `public/geo/types_{지역}.geojson` 폴리곤을 유형별로 색칠한다(긴급방문형·연계형·예방인프라형·관찰형).
- 질문 응답의 `display.map.points` 는 칸 중심점이다. `types` 레이어는 50행 제한 이슈가 있어 관리자 유형 지도는 points 가 아니라 GeoJSON 전체를 기준으로 색칠하고, points 의 `highlight` 칸만 굵은 테두리로 강조한다.
- 시설(`facilities_*.geojson`)은 점. 강남·춘천 bbox 를 벗어난 점은 그리지 않는다(원천 데이터 좌표 오류 4건: 봉은테니스장, 역삼청소년수련관수영장, 대치유수지체육공원축구장, 꿈자람구장).
- `cell_id`·`fac_id` 는 툴팁·카드에 쓰지 않고 조회 키로만 쓴다.

## 지킬 것 (agent/README.md 7절, engine/지도_규격.md)

- 질문 응답의 `display` 만 그린다. `internal` 은 받지도 그리지도 않는다.
- 시민 화면에 위험 판정·고립 유형·신뢰도·후보 격자를 노출하지 않는다.
- 시민의 찾을 위치는 저장하지 않는다(메모리에만).
- 함께 가기·이동 도움 요청은 자동 매칭 없이 담당자가 확인한 뒤 연결한다.
- `agent/`, `engine/` 폴더는 읽기만 하고 수정하지 않는다.

## 임시 처리 (백엔드 API 가 생기면 교체)

| 항목 | 지금 | 교체 지점 |
| --- | --- | --- |
| 현장 확인 목록 전달 | 목업: 공유 저장소 / 실제: `.json` 내려받기 → 현장 앱 "목록 불러오기" | `api/types.ts` 의 `publishFieldCheckList`, `fetchFieldCheckList` |
| 현장 판정 덮어쓰기(`has_residents=no` 숨김, `support_needed=not_needed` → 관찰형) | 프론트가 `GET /field-checks` 를 읽어 지도에만 적용 | `map/applyFieldOverrides.ts` 삭제 후 GeoJSON `field_status` 사용 |
| GeoJSON 제공 | `public/geo/` 정적 복사본 | `VITE_GEO_BASE_URL` |
| 시민 일정, 큰 글씨 설정 | 기기 localStorage | 필요하면 백엔드 |
| 시설 전화번호 | 데이터에 없어 카드에 전화 버튼 없음 | 시설 데이터에 전화 필드가 생기면 `PlaceCard` |
| 주민센터 전화 | `src/config.ts` `communityCenterPhone` 비어 있음(버튼 숨김) | 번호 확인 후 채우기 |

## 백엔드와 확인된 것 (2026-10-12, 실제 서버에 curl)

- 회원가입·로그인·401/403 오류 형식·CORS(localhost:5173) 모두 계약서대로 동작. 이메일은 `.local` 같은 예약 도메인을 거부하므로 `example.com` 등을 쓴다.
- 지원 요청 생성/목록/상태 변경, 현장 기록 생성/조회: 프론트가 보내는 payload 그대로 201/200.
- checklist 는 현장기록 규격의 문자열 값(`yes/no/unknown`, `needed/not_needed/unsure`)으로 저장되고 그대로 조회된다.
- `GET /admin/field-feedback-summary` 응답 키는 `checklist_responses` (계약서에는 키 이름이 없었음). `unknown` 답도 응답으로 센다 → 채원에게 전달.
- 날짜 `created_at` 은 `"YYYY-MM-DD HH:MM:SS"` (UTC, 시간대 없음) 형식이라 `lib/datetime.ts` 에서 보정한다.
- 질문 API 는 Anthropic 키가 없으면 500 `internal_server_error` 를 돌려준다. 프론트는 안내 문구로 바꿔 보여준다.

## 팀에 전달할 것

- `types` 레이어 points 50개 제한(hyunjun 10/12 수정분이 sarang 의 engine 복사본에 반영됐는지), 시설 좌표 이상치 4건.
- 현장 확인 목록 전달 API, 현장 판정 덮어쓰기(백엔드), GeoJSON 정적 서빙 여부.
