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
| GET | `/api/v1/maps/facilities?region=<REGION>` | `citizen`, `admin` |
| GET | `/api/v1/admin/maps/types?region=<REGION>&show_excluded=<BOOL>` | `admin` |
| GET | `/api/v1/admin/maps/candidates?region=<REGION>` | `admin` |
| GET | `/api/v1/admin/maps/placements?region=<REGION>&radius_m=<METERS>&sites=<COUNT>` | `admin` |
| POST | `/api/v1/support-requests` | `citizen` |
| GET | `/api/v1/support-requests?status=<STATUS>` | `admin` |
| GET | `/api/v1/support-requests/<REQUEST_ID>` | `admin` |
| PATCH | `/api/v1/support-requests/<REQUEST_ID>/status` | `admin` |
| GET | `/api/v1/field-check-list` | `field_worker` |
| PUT | `/api/v1/field-check-list` | `field_worker` |
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

### 지도

지도 API는 `engine/out`의 GeoJSON을 읽기 전용으로 제공한다. 지역은 `강남`, `춘천`만 허용한다.
인증 누락·무효는 `401`, 허용되지 않은 역할은 `403`, 허용되지 않은 지역·배치 선택값은 `422`다.

**GET `/api/v1/maps/facilities?region=<REGION>`** — `citizen`, `admin`.

성공 응답은 시설 GeoJSON `FeatureCollection`이다. 시민 응답의 feature properties는
`fac_id`, `name`, `addr`, `kind`, `group`만 포함하며 후보·유형·배치·위험도·현장기록 정보는
포함하지 않는다. `fac_id`는 시설 연결에 쓰는 내부 키다. **프론트엔드는 `fac_id`를 화면에
글자로 표시하면 안 된다.**

**GET `/api/v1/admin/maps/types?region=<REGION>&show_excluded=<BOOL>`** — `admin`.

전체 격자 유형 GeoJSON을 반환한다. `show_excluded`는 기본 `false`이며,
`true`일 때 현장 확인으로 제외된 칸을 포함한다. 최신 현장기록이 있는 칸에는
`field_status`, `field_checked_at` 및 보존된 엔진 판정(`engine_type`, `engine_priority`)이
포함될 수 있다. 지원 불필요 판정은 `type=관찰형`, `priority=4`로 반환한다.

**GET `/api/v1/admin/maps/candidates?region=<REGION>`** — `admin`.

후보 칸 GeoJSON을 반환한다.

**GET `/api/v1/admin/maps/placements?region=<REGION>&radius_m=<METERS>&sites=<COUNT>`** — `admin`.

거점 배치 GeoJSON을 반환한다. 허용 반경은 `1000`, `3000`m이며 거점 수는 현재 파일이 있는
`3`만 허용한다.

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

#### 현장 확인 목록 동기화

현장 담당자가 가져온 확인 목록은 담당자 계정별로 저장한다. 같은 계정으로 다른 기기에서
로그인해도 목록을 다시 조회할 수 있다. 이 API는 요청 경로·본문에 사용자 ID를 받지 않고
인증된 `field_worker` 본인 목록만 처리한다. 다른 현장 담당자는 자신의 목록만 보며,
시민·관리자 역할은 저장·조회할 수 없다.

목록은 `{ region, headline, created_at, cells }` 형식이며, 서버가 각 필드와 셀 항목을
엄격히 검증한다. 알 수 없는 추가 필드, 필수 필드 누락, 빈 `cells`, 잘못된 좌표·순번,
시간대가 없는 `created_at`은 `422 validation_error`를 반환한다.

**GET `/api/v1/field-check-list`** — `field_worker`.

현재 로그인한 담당자의 목록을 반환한다. 아직 저장된 목록이 없으면 `null`을 반환한다.
토큰 누락·무효는 `401`, 다른 역할은 `403`이다.

**PUT `/api/v1/field-check-list`** — `field_worker`.

요청은 업로드 파일의 목록 JSON이고, 성공 응답은 기존 목록과 병합된 전체 목록이다.
기존 셀은 유지하고 새 `id`는 뒤에 추가한다. 같은 `id`가 있으면 기존 위치에서 새 파일의
셀 내용으로 갱신하며, 응답의 `order`는 병합된 순서대로 다시 매긴다. `region`, `headline`,
`created_at`은 가장 최근 업로드 파일의 값을 사용한다. 병합·저장은 한 트랜잭션으로 처리하며
현장기록(`/api/v1/field-checks`)은 변경하거나 삭제하지 않는다. 파일 업로드는 검증과 서버 저장이
성공하고 병합된 전체 응답을 받은 뒤 화면에 반영한다. 백엔드 저장 실패나 유효하지 않은 응답은
성공으로 취급하지 않는다.

```json
{
  "region": "춘천",
  "headline": "테스트용 현장 확인 목록",
  "created_at": "2026-10-18T01:00:00+09:00",
  "cells": [
    {
      "id": "4026_7935",
      "lat": 37.8546,
      "lon": 127.5753,
      "emd_name": "서면",
      "level": "확인 필요",
      "questions": ["실제로 사람이 사는 집이 있나요?"],
      "order": 1,
      "highlight": false
    }
  ]
}
```

**POST `/api/v1/field-checks`** — `field_worker`, `admin`.

요청:

```json
{
  "cell_id": "<CELL_ID>",
  "checklist": {
    "has_residents": "yes",
    "social_hard_to_reach": "unknown",
    "health_hard_to_reach": "unknown",
    "seniors_out_daytime": "unknown",
    "support_needed": "needed"
  },
  "checked_at": "<ISO_8601_DATETIME>",
  "note": "<NOTE>"
}
```

`has_residents`, `social_hard_to_reach`, `health_hard_to_reach`, `seniors_out_daytime`는
`yes`, `no`, `unknown`을 사용하고, `support_needed`는 `needed`, `not_needed`, `unsure`를
사용한다. `checklist`의 나머지 값과 `note`는 그대로 저장되며 판정 덮어쓰기는 위 두 규칙만 적용한다.

성공 응답 핵심 필드: `id`, `cell_id`, `checklist`, `checked_at`, `note`, `created_at`.
토큰 누락·무효는 `401`, 시민 역할은 `403`.

**GET `/api/v1/field-checks?cell_id=<CELL_ID>`** — `field_worker`, `admin`.

성공 응답은 해당 셀의 현장 확인 기록 목록이다. 원본 현장 확인 내용을 포함하므로 인가된
현장 담당자·관리자만 사용해야 한다. 토큰 누락·무효는 `401`, 시민 역할은 `403`.

유형 지도에는 칸별 `checked_at`이 가장 최신인 기록 하나만 반영한다. `has_residents=no`는
`excluded`로 분류해 기본 지도에서 숨기며, 두 규칙이 함께 맞으면 제외가 우선한다.
그 외에 `support_needed=not_needed`는 `관찰형`(우선순위 4)으로 낮춘다.
최신 기록의 값이 `unknown`/`unsure`이거나 두 규칙에 해당하지 않으면 이전 기록으로 되돌아가지
않고 엔진 판정을 유지한다. 변경 시 원본 유형·우선순위를 `engine_type`, `engine_priority`로
보존하고, `field_status`, `field_checked_at`을 함께 반환한다. 원본 엔진 GeoJSON 파일은 변경하지 않는다.
현장기록은 관리자 유형 지도에서만 사용하며 시민 지도 API에는 포함하지 않는다.

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

- 문서 생성 결과 다운로드 API는 아직 없다.
- 계정 관리·권한 변경 공개 API는 없다.

실제 이메일, 비밀번호, JWT/API 키, 토큰, 사용자 개인정보를 이 문서나 Git에 기록하지 않는다.
