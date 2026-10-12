/**
 * ⚠️ 임시 처리 (프론트 로컬 계산).
 * engine/현장기록_규격.md 2절의 "판정 반영"은 백엔드가 하기로 합의됐지만 아직 구현되지 않아,
 * 프론트가 저장된 현장 기록(GET /api/v1/field-checks)을 읽어 같은 규칙을 지도에만 적용한다.
 * 백엔드가 types_*.geojson / display.map.points 에 field_status 를 붙여 주기 시작하면 이 파일을 지우고
 * properties.field_status 를 그대로 쓰면 된다. 에이전트 답변 속 숫자에는 반영되지 않는다 (규격 5절).
 */
import type { FieldCheck } from '@/types/api'
import type { FieldStatus, GridCollection } from '@/types/geo'

export interface FieldOverride {
  status: FieldStatus
  checked_at: string
}

/** 칸마다 가장 최근 기록 하나를 골라 규칙 1(제외) → 규칙 2(관찰형으로) 순서로 판정한다 */
export function computeFieldOverrides(checks: FieldCheck[]): Map<string, FieldOverride> {
  const latest = new Map<string, FieldCheck>()
  for (const c of checks) {
    const prev = latest.get(c.cell_id)
    if (!prev || Date.parse(c.checked_at) > Date.parse(prev.checked_at)) latest.set(c.cell_id, c)
  }
  const out = new Map<string, FieldOverride>()
  for (const [cellId, c] of latest) {
    if (c.checklist.has_residents === 'no') out.set(cellId, { status: 'excluded', checked_at: c.checked_at })
    else if (c.checklist.support_needed === 'not_needed') out.set(cellId, { status: 'downgraded', checked_at: c.checked_at })
  }
  return out
}

/** 유형 지도에 덮어쓰기를 반영한 새 FeatureCollection. excluded 칸은 showExcluded 가 아니면 뺀다 */
export function applyFieldOverrides(
  data: GridCollection,
  overrides: Map<string, FieldOverride>,
  opts: { showExcluded?: boolean } = {},
): GridCollection {
  if (overrides.size === 0) return data
  const features = []
  for (const f of data.features) {
    const o = overrides.get(f.properties.cell_id)
    if (!o) {
      features.push(f)
      continue
    }
    if (o.status === 'excluded' && !opts.showExcluded) continue
    const props = { ...f.properties, field_status: o.status, engine_type: f.properties.type, field_checked_at: o.checked_at }
    if (o.status === 'downgraded') {
      props.type = '관찰형'
      props.priority = 4
    }
    features.push({ ...f, properties: props })
  }
  return { ...data, features }
}
