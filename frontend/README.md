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
| `npm test` | 현장 목록 API 경로·기기 간 동기화 테스트 |
| `node scripts/screenshot.mjs [out-dir] [prefix]` | Playwright 로 화면별 스크린샷 (개발 서버 필요). 실제 API 점검은 `BASE_URL=http://localhost:5173 ADMIN_PASSWORD=... ONLY=maps node scripts/screenshot.mjs design real-` |
| `npm run sync-geo` | `engine/out/*.geojson` → `public/geo/` 복사 (시설 지도는 `origin/hyunjun` 에서 추출) |

## 환경 변수 (`.env`, 커밋하지 않음)

| 변수 | 기본값 | 뜻 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | 빈 값(프론트와 같은 출처) | FastAPI 백엔드 주소. 별도 도메인에 배포하면 빌드 시 API 주소를 명시 |
| `VITE_USE_MOCK` | `true` | `true`면 백엔드 없이 목업으로 전 화면 동작 |
| `VITE_GEO_BASE_URL` | `/geo` | 목업 모드에서만 읽는 격자·시설 GeoJSON 위치 |

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

개발 모드에서는 `VITE_API_BASE_URL=http://localhost:8000 VITE_USE_MOCK=false npm run dev` 로 실행한다. 배포 기본값은 같은 출처이며, 프론트와 백엔드가 서로 다른 도메인이라면 프론트 빌드 시 `VITE_API_BASE_URL` 을 백엔드 주소로 지정하고 백엔드의 허용 출처 설정도 맞춰야 한다. 브라우저는 `http://localhost:5173` 으로 연다 (백엔드 CORS 기본 허용 목록이 `localhost` 라 `127.0.0.1` 로 열면 요청이 막힌다). 현장 확인 목록은 담당자 계정에 저장되며, 같은 계정의 새 기기 로그인에서 API를 다시 조회한다. 시민 계정은 로그인 화면의 "시민 계정 만들기"로 가입한다(비밀번호 12자 이상). 관리자·현장 계정은 운영자가 만든다(`backend/seed_user.py` 또는 배포 환경 변수 `SEED_*`). 질문 API 는 `agent/.env` 의 Anthropic 키가 있어야 실제 답을 돌려준다.

## 시연 시나리오 (목업 모드)

| 역할 | 흐름 |
| --- | --- |
| 관리자 ① | 로그인 → 지도와 질문 → "춘천에서 어디부터 확인해야 해?" → 결론·신뢰도, 언급된 행정동 칸이 지도에 강조 |
| 관리자 ② | "춘천 외곽에 거점 3곳을 둔다면 이동형이랑 경로당 거점 중 뭐가 나아?" → 막대그래프 + 거점 지도 |
| 관리자 ③ | "춘천 외곽 이동형 건강상담 사업 제안서 써줘" → 문서 조각 → `.md 내려받기` |
| 관리자 ④ | "춘천 현장 확인 목록 만들어 줘" → `이 목록을 현장 담당자에게 보내기` → 현장 확인 목록 화면 |
| 시민 | 위치 고르기(지도에서 춘천 시내 클릭) → "어머니 댁 근처에 다니실 만한 곳 있어요?" → 장소 카드 → `함께 갈 이웃 찾기` → 요청 보내기 → 관리자 "시민 요청" 탭에 대기 건으로 표시 |
| 현장 | 로그인 → 관리자가 보낸 목록 → 동네 선택 → 버튼 답변 + "지원 필요 여부" + 메모 → 저장 → 목록에 "저장됨". `has_residents = 아니오` 로 저장하면 관리자 지도에서 그 칸이 사라진다(임시 처리) |

## 디자인

기준 시안은 [design/citizen-mock.png](design/citizen-mock.png) (구성·위계·여백의 기준, 색은 파란색 주색 유지). 화면별 최종 스크린샷은 `design/*.png` 에 있고 `node scripts/screenshot.mjs design` 으로 다시 찍는다(개발 서버가 목업 모드로 떠 있어야 함. 시민·현장 390px, 관리자·로그인 1440px).

- 색·둥글기·글꼴은 `src/index.css` 의 `@theme` 토큰 한 곳에서 정의한다 (`bg-primary`, `text-ink-3`, `rounded-card` 등으로 사용).
- 테두리 박스는 장소 카드·목록 행·강조 패널에만 쓴다. 박스 안에 박스를 넣지 않고 그림자는 쓰지 않는다.
- 한 구획에 채움 버튼은 하나. 자주 안 쓰는 동작은 `Menu`(점 세 개)나 `Sheet`(바텀 시트)로.
- 아이콘은 lucide-react. 지도 번호 마커는 1 초록, 2 파랑, 3 주황.
- 공통 부품: `Button`(fill/outline/text/dark), `SegmentedControl`, `Sheet`, `List`/`ListRow`, `DayChip`, `Menu`, `PlaceCard`, `HeaderActions`(PC/모바일 전환 + 로그아웃).
- 시민·현장 화면은 기본 430px 단일 컬럼이고, 상단 "PC 화면" 버튼으로 1040px 2단 보기(답변·지도 | 일정·도움 / 목록 | 지도)로 바꿀 수 있다. 선택은 기기에 기억된다(`features/viewMode.ts`). 로그아웃은 모든 역할에서 상단의 단일 버튼이다.

## 폴더 구조

```
src/
  api/            client.ts (fetch·토큰·오류·Retry-After)  endpoints.ts (계약서 1:1)  types.ts (인터페이스)
                  mock/ (데모 계정, localStorage 저장소, fixtures/ 화면조각 19개, 키워드 매칭)  index.ts (스위치)
  auth/           AuthProvider, useAuth, RequireRole (역할 가드), roleHome
  types/          api.ts (docs/api-contract.md)  display.ts (에이전트 화면 조각)  geo.ts (GeoJSON properties)
  config.ts       환경 변수, 지역(강남·춘천) 중심·bbox, 주민센터 전화 자리
  fragments/      toFragments (display → 조각 배열, 모드별 순서)  registry  FragmentRenderer  components/ 조각 8종
  map/            BaseMap(OSM)  GridLayer(격자 색칠)  PointsLayer(레이어별 점)  markers  colors  API 기반 useGeoLayer
  features/       citizen/ (세션, 접근성, 지오코딩, 공유, 일정)  admin/ (현장 목록 변환)  field/ (체크리스트 키, 저장 표시)
  components/     ui/ 공통(Button·SegmentedControl·Sheet·ListRow·DayChip·Menu), QuestionBox(관리자), map/ (지역 탭·범례), citizen/ (헤더·위치 시트·질문 바·장소 카드·이번 주·도움 패널)
  layouts/        AppShell (관리자 상단 메뉴 / 시민·현장 하단 탭), 역할별 레이아웃
  pages/          login, admin/, citizen/, field/
  lib/            queryClient, useAskQuestion, download, geoIndex (ID → 이름)
public/geo/       격자·시설 GeoJSON (engine/out 복사본, WGS84)
scripts/          sync-geo.sh
```

### 라우트와 권한

| 경로 | 역할 | 화면 |
| --- | --- | --- |
| `/login` | 공개 | 로그인, 시민 가입 |
| `/admin` | admin | 지도(유형 / 후보 / 배치 레이어 전환, 지역 공통) + 질문창 + 응답 조각, 현장 목록 보내기 |
| `/admin/requests` | admin | 시민 요청 목록(승인·반려·완료), 수요 신호·현장 피드백 집계 |
| `/admin/field-list` | admin | 현장 확인 목록 생성·보내기·복사·내려받기 |
| `/citizen` | citizen | 위치 한 줄(시트로 변경), 질문 말풍선, 답변, 번호 지도, 장소 카드 3개, 이번 주, 도움 패널, 공유·전화. 하단 고정 질문 바(마이크) |
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

- 좌표계는 WGS84(경도, 위도)라 변환 없이 Leaflet 에 올린다. 실제 모드는 시민 시설·관리자 유형 지도 API를 사용하고 목업 모드만 `public/geo/` GeoJSON fixture를 읽는다.
- 질문 응답의 `display.map.points` 는 칸 중심점이다. 관리자 유형 지도는 서버 GeoJSON 전체를 기준으로 색칠하고, 응답 points 의 `highlight` 칸만 굵은 테두리로 강조한다.
- 시민 시설 목록은 `GET /api/v1/maps/facilities?region=...` allowlist에 포함된 시설만 표시한다. `fac_id`·`cell_id` 는 툴팁·카드에 쓰지 않고 조회 키로만 쓴다.
- `cell_id`·`fac_id` 는 툴팁·카드에 쓰지 않고 조회 키로만 쓴다.

### 관리자 지도 레이어

| 레이어 | 데이터 | 색 | 범례·팝업 |
| --- | --- | --- | --- |
| 유형 | `GET /admin/maps/types` (`types_{지역}`) | 4유형 | 유형 범례(필터), 현장 확인 제외 보기 |
| 후보 | `GET /admin/maps/candidates` (`candidates_{지역}`) | `persistent_months` 4/5/6 → 연한→진한 주황, `res_status` 용도미상은 점선 테두리 | 개월별 수, 격자 팝업(동네·지속 개월·거주 상태) |
| 배치 | `GET /admin/maps/placements` (`sim_{지역}_k3_r{1000\|3000}`) | `covered` 1 파랑 / 0 주황 | 반경 1km·3km 전환, 커버 집계(배치 전 공백 → 후), 응답 거점 ★ + '닿는 N곳' 라벨 |

레이어를 바꿔도 지도 위치·줌은 유지되고(범위는 지역이 바뀔 때만 맞춤), 질문 응답의 레이어(candidates → 후보, sites·interventions → 배치)에 맞춰 자동으로 전환된다. 목업 모드는 `public/geo` 파일을, 실제 모드는 지도 API 를 읽는다.

## 지킬 것 (agent/README.md 7절, engine/지도_규격.md)

- 질문 응답의 `display` 만 그린다. `internal` 은 받지도 그리지도 않는다.
- 시민 화면에 위험 판정·고립 유형·신뢰도·후보 격자를 노출하지 않는다.
- 시민의 찾을 위치는 저장하지 않는다(메모리에만).
- 함께 가기·이동 도움 요청은 자동 매칭 없이 담당자가 확인한 뒤 연결한다.
- `agent/`, `engine/` 폴더는 읽기만 하고 수정하지 않는다.

## API 연결 상태

| 항목 | 지금 | 교체 지점 |
| --- | --- | --- |
| 지도 조회 | 실제 모드: 시민 시설·관리자 유형/후보/배치 API, 목업: `public/geo/` 정적 복사본 | `api/types.ts`, `api/endpoints.ts`, `api/mock/index.ts` |
| 현장 판정 덮어쓰기 | 실제 모드: 관리자 유형 지도 응답의 `field_status`, `engine_type`, `engine_priority`, `field_checked_at` 사용 | `map/useGeoLayer.ts`, `map/GridLayer.tsx` |
| 현장 확인 목록 전달 | 목업: 공유 저장소 / 실제: 전달·조회 API 미지원. JSON 직접 다운로드·가져오기만 가능 | 백엔드 API가 제공되면 `publishFieldCheckList`, `fetchFieldCheckList` 연결 |
| 시민 일정, 큰 글씨 설정 | 기기 localStorage | 필요하면 백엔드 |
| 시설 전화번호 | 데이터에 없어 카드에 전화 버튼 없음 | 시설 데이터에 전화 필드가 생기면 `PlaceCard` |
| 주민센터 전화 | `src/config.ts` `communityCenterPhone` 비어 있음(버튼 숨김) | 번호 확인 후 채우기 |

## 백엔드와 확인된 것 (2026-10-12, 실제 서버에 curl)

- 회원가입·로그인·401/403 오류 형식·CORS(localhost:5173) 모두 계약서대로 동작. 이메일은 `.local` 같은 예약 도메인을 거부하므로 `example.com` 등을 쓴다.
- 지원 요청 생성/목록/상태 변경, 현장 기록 생성/조회: 프론트가 보내는 payload 그대로 201/200.
- checklist 는 현장기록 규격의 문자열 값(`yes/no/unknown`, `needed/not_needed/unsure`)으로 저장되고 그대로 조회된다.
- 시민 시설 지도는 `GET /api/v1/maps/facilities?region=...`, 관리자 지도는 유형·후보·배치별 관리자 API를 사용한다. 시민 시설 응답은 allowlist 속성만 포함하며 `fac_id`는 화면에 표시하지 않는다.
- 관리자 유형 지도는 서버가 처리한 최신 현장기록을 사용한다. `has_residents=no`가 제외 우선이고 `support_needed=not_needed`는 관찰형/우선순위 4로 표시된다. 원본 엔진 값은 별도 속성에 보존한다.
- 관리자와 현장 담당자 사이의 목록 전달 API는 아직 없다. 실제 모드의 목록은 JSON 직접 전달이며, 현장 앱에서 가져온 목록은 현재 탭 세션에만 보관한다.
- `GET /admin/field-feedback-summary` 응답 키는 `checklist_responses` (계약서에는 키 이름이 없었음). `unknown` 답도 응답으로 센다 → 채원에게 전달.
- 날짜 `created_at` 은 `"YYYY-MM-DD HH:MM:SS"` (UTC, 시간대 없음) 형식이라 `lib/datetime.ts` 에서 보정한다.
- 질문 API 는 Anthropic 키가 없으면 500 `internal_server_error` 를 돌려준다. 프론트는 안내 문구로 바꿔 보여준다.

## 팀에 전달할 것

- `types` 레이어 points 50개 제한(hyunjun 10/12 수정분이 sarang 의 engine 복사본에 반영됐는지), 시설 좌표 이상치 4건.
- 현장 확인 목록 전달 API, 현장 판정 덮어쓰기(백엔드), GeoJSON 정적 서빙 여부.
