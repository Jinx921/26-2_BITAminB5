# 백엔드 API 계약

기본 URL은 로컬 개발에서 `http://127.0.0.1:8000`이다. OpenAPI/Swagger는
`/docs`에서 확인할 수 있다. JSON 요청에는 `Content-Type: application/json`을 사용한다.

인증이 필요한 경로는 로그인 응답의 토큰을 다음 헤더로 전달한다.
문서의 모든 값은 예시 또는 자리표시자이며 실제 자격 증명·토큰이 아니다.

```http
Authorization: Bearer <ACCESS_TOKEN>
```

오류는 공통 형식으로 반환한다.

```json
{
  "error": {
    "code": "unauthorized",
    "message": "Authentication required"
  },
  "request_id": "<REQUEST_ID>"
}
```

- `401`: 누락·유효하지 않은 토큰, 또는 로그인 자격 증명 오류.
- `403`: 토큰은 유효하지만 해당 역할에 권한이 없음.
- 입력 검증 오류는 `422`, 존재하지 않는 리소스는 `404`를 사용한다.

## 엔드포인트

| 메서드 | 경로 | 필요한 역할 |
| --- | --- | --- |
| GET | `/health` | 공개 |
| POST | `/api/v1/auth/register` | 공개 (시민 계정만 생성) |
| POST | `/api/v1/auth/login` | 공개 |
| POST | `/api/v1/questions` | `citizen`, `admin` |
| POST | `/api/v1/support-requests` | `citizen` |
| GET | `/api/v1/support-requests?status=<STATUS>` | `admin` |
| GET | `/api/v1/support-requests/<REQUEST_ID>` | `admin` |
| PATCH | `/api/v1/support-requests/<REQUEST_ID>/status` | `admin` |
| POST | `/api/v1/field-checks` | `field_worker`, `admin` |
| GET | `/api/v1/field-checks?cell_id=<CELL_ID>` | `field_worker`, `admin` |
| GET | `/api/v1/admin/demand-signals` | `admin` |
| GET | `/api/v1/admin/field-feedback-summary` | `admin` |

### 상태 확인

**GET `/health`** — 인증 불필요.

성공 응답 핵심 필드:

```json
{"status": "ok"}
```

### 회원가입 및 로그인

**POST `/api/v1/auth/register`** — 공개 시민 회원가입.

요청:

```json
{"email": "<EMAIL>", "password": "<PASSWORD_AT_LEAST_12_CHARACTERS>"}
```

성공 응답은 `id`, `email`, `role`, `created_at`을 포함한다. 새 계정의 `role`은 항상
`citizen`이며 비밀번호 해시는 응답에 포함하지 않는다. 이메일 중복·생성 실패는
계정 존재 여부를 노출하지 않는 `409` 공통 오류를 반환한다. `401`/`403`은 적용되지 않는다.

**POST `/api/v1/auth/login`** — 공개 로그인.

요청:

```json
{"email": "<EMAIL>", "password": "<PASSWORD>"}
```

성공 응답 핵심 필드:

```json
{
  "access_token": "<ACCESS_TOKEN>",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {"id": 1, "email": "<EMAIL>", "role": "citizen"}
}
```

잘못된 이메일·비밀번호는 계정 존재 여부와 무관하게 `401` `invalid_credentials`를 반환한다.
인증 헤더는 필요하지 않으며 `403`은 적용되지 않는다.

### 질문

**POST `/api/v1/questions`** — `citizen`, `admin`.

요청:

```json
{
  "mode": "citizen",
  "question": "<QUESTION>",
  "location": {"lat": 37.0, "lon": 127.0}
}
```

시민은 `location`을 생략할 수 있다. `mode`는 기존 클라이언트 호환을 위해 요청에 남아 있지만,
실제 모드는 로그인 계정의 역할로 결정된다: 시민은 `citizen`, 관리자는 `admin`.
관리자 요청에는 location을 전달하지 않는다. 현장 담당자는 사용할 수 없다.

성공 응답은 screen 전체가 아니라 **`screen["display"]` 객체만** 반환한다.
프론트엔드는 이 display 데이터만 렌더링하고 `internal`, 도구 추적, 검증 정보를 기대하거나 표시하면 안 된다.
display에는 `headline`, `details`, `caution`, `confidence`, `map` 등이 포함될 수 있다.
권한이 없거나 토큰이 유효하지 않으면 각각 `403` 또는 `401`을 반환한다.

### 지원 요청

**POST `/api/v1/support-requests`** — `citizen`.

요청:

```json
{
  "facility_id": "<FACILITY_ID>",
  "requester_name": "<REQUESTER_NAME>",
  "contact": "<CONTACT>",
  "contact_consent": true,
  "requested_at": "<ISO_8601_DATETIME>",
  "request_type": "companion",
  "note": "<NOTE>"
}
```

`request_type`은 `companion` 또는 `mobility`다. 연락처는 `contact_consent: true`일 때만 저장된다.
새 요청은 자동 매칭·승인 없이 `pending`에서 시작한다.
성공 응답 핵심 필드: `id`, 요청 필드, `contact_consent`, `status`, `created_at`.
토큰 누락·무효는 `401`, 시민이 아닌 역할은 `403`.

**GET `/api/v1/support-requests?status=<STATUS>`** — `admin`.

`status`는 선택 사항이며 `pending`, `approved`, `rejected`, `completed`를 지원한다.
성공 응답은 지원 요청 객체 목록을 반환하며 각 항목은 `id`, `facility_id`, 요청 유형,
상태와 저장된 요청 정보를 포함한다. 개인 정보가 포함될 수 있는 관리자 전용 응답이다.
토큰 누락·무효는 `401`, 비관리자 접근은 `403`.

**GET `/api/v1/support-requests/<REQUEST_ID>`** — `admin`.

성공 응답은 해당 지원 요청 객체를 반환한다. 토큰 누락·무효는 `401`,
비관리자 접근은 `403`, ID가 없으면 `404`.

**PATCH `/api/v1/support-requests/<REQUEST_ID>/status`** — `admin`.

요청:

```json
{"status": "approved"}
```

허용 상태는 `pending`, `approved`, `rejected`, `completed`.
성공 응답은 업데이트된 지원 요청 객체(`id`, `status` 등)를 반환한다.
토큰 누락·무효는 `401`, 비관리자 접근은 `403`, ID가 없으면 `404`.

### 현장 확인

**POST `/api/v1/field-checks`** — `field_worker`, `admin`.

요청:

```json
{
  "cell_id": "<CELL_ID>",
  "checklist": {"<ITEM>": true},
  "checked_at": "<ISO_8601_DATETIME>",
  "note": "<NOTE>"
}
```

성공 응답 핵심 필드: `id`, `cell_id`, `checklist`, `checked_at`, `note`, `created_at`.
토큰 누락·무효는 `401`, 시민 역할은 `403`.

**GET `/api/v1/field-checks?cell_id=<CELL_ID>`** — `field_worker`, `admin`.

성공 응답은 해당 셀의 현장 확인 기록 목록이다. 원본 현장 확인 내용을 포함하므로 인가된
현장 담당자·관리자만 사용해야 한다. 토큰 누락·무효는 `401`, 시민 역할은 `403`.

### 관리자 운영 신호

**GET `/api/v1/admin/demand-signals`** — `admin`.

요청별 원본이 아닌 `facility_id`, `request_type`, `status`, `count` 집계 목록을 반환한다.
3건 미만 버킷은 응답에서 제외한다. 결과가 없으면 빈 배열을 반환한다.
연락처·이메일·이름·메모는 포함하지 않는다. 토큰 누락·무효는 `401`, 비관리자 접근은 `403`.

**GET `/api/v1/admin/field-feedback-summary`** — `admin`.

성공 응답은 셀별 `cell_id`, `checked_count`, 그리고 각 셀 내 체크리스트 항목별
`item_index`, `response_count` 목록을 반환한다. 체크리스트 원래 항목명과 현장 메모는 반환하지 않는다.
결과가 없으면 빈 배열을 반환한다. 토큰 누락·무효는 `401`, 비관리자 접근은 `403`.
이 신호는 향후 데이터 계약 확정 후 전달할 수 있는 집계이며 현재 agent·engine 동작에는 반영되지 않는다.

## 아직 제공하지 않는 API

- 지도 전용 조회 API는 아직 없다. 질문 응답의 `display.map`은 질문 결과의 일부다.
- 문서 생성 결과 다운로드 API는 아직 없다.
- 계정 관리·권한 변경 공개 API는 없다.

실제 이메일, 비밀번호, JWT/API 키, 토큰, 사용자 개인정보를 이 문서나 Git에 기록하지 않는다.
