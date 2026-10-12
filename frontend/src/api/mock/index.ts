/** ApiClient 목업 구현. 실제 백엔드와 같은 권한 규칙·오류 코드를 흉내낸다. */
import { ApiError, tokenStore } from '../client'
import type { ApiClient } from '../types'
import { DEMO_ACCOUNTS, demoUser, roleFromMockToken } from './accounts'
import { mockAnswer } from './questions'
import { mockStore } from './store'
import type { DemandSignal, FieldCheck, FieldFeedbackSummary, Role, SupportRequest } from '@/types/api'
import { env, type RegionKey } from '@/config'
import type { FacilityCollection, GridCollection } from '@/types/geo'

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

function currentRole(): Role {
  const role = roleFromMockToken(tokenStore.get()?.token)
  if (!role) throw new ApiError(401, 'unauthorized', 'Authentication required')
  return role
}

function requireRole(...allowed: Role[]): Role {
  const role = currentRole()
  if (!allowed.includes(role)) throw new ApiError(403, 'forbidden', 'Insufficient role')
  return role
}

async function loadMockGeoJson<T>(name: string): Promise<T> {
  const response = await fetch(`${env.geoBaseUrl}/${encodeURIComponent(name)}.geojson`)
  if (!response.ok) throw new Error(`지도 파일을 불러오지 못했습니다 (${name}.geojson, ${response.status})`)
  return (await response.json()) as T
}

const mockGeoApi = {
  facilities: (region: RegionKey) => loadMockGeoJson<FacilityCollection>(`facilities_${region}`),
  types: (region: RegionKey) => loadMockGeoJson<GridCollection>(`types_${region}`),
  candidates: (region: RegionKey) => loadMockGeoJson<GridCollection>(`candidates_${region}`),
  placements: (region: RegionKey, radiusM: 1000 | 3000, sites: 3) =>
    loadMockGeoJson<GridCollection>(`sim_${region}_k${sites}_r${radiusM}`),
}

export const mockApi: ApiClient = {
  async health() {
    await delay(100)
    return { status: 'ok' }
  },

  async register(email, password) {
    await delay(300)
    if (password.length < 12) throw new ApiError(422, 'validation_error', 'Request validation failed')
    if (DEMO_ACCOUNTS.some((a) => a.email === email)) throw new ApiError(409, 'conflict', 'Unable to create account')
    return { id: 100, email, role: 'citizen', created_at: new Date().toISOString() }
  },

  async login(email, password) {
    await delay(400)
    const idx = DEMO_ACCOUNTS.findIndex((a) => a.email === email.toLowerCase() && a.password === password)
    if (idx < 0) throw new ApiError(401, 'invalid_credentials', 'Invalid email or password')
    const acc = DEMO_ACCOUNTS[idx]
    return {
      access_token: `mock.${acc.role}.${Date.now()}`,
      token_type: 'bearer',
      expires_in: 3600,
      user: demoUser(acc, idx + 1),
    }
  },

  async askQuestion(req, signal) {
    const role = requireRole('admin', 'citizen') as 'admin' | 'citizen'
    if (role === 'admin' && req.location) throw new ApiError(422, 'validation_error', 'location is only supported for citizen accounts')
    await delay(1500)
    if (signal?.aborted) throw new DOMException('aborted', 'AbortError')
    return mockAnswer(req, role)
  },

  async createSupportRequest(body) {
    requireRole('citizen')
    await delay(300)
    const row: SupportRequest = {
      ...body,
      contact: body.contact_consent ? (body.contact ?? null) : null,
      note: body.note ?? '',
      id: mockStore.nextId(),
      status: 'pending',
      created_at: new Date().toISOString(),
    }
    mockStore.update((s) => s.supportRequests.push(row))
    return row
  },

  async listSupportRequests(status) {
    requireRole('admin')
    await delay(250)
    const rows = mockStore.get().supportRequests
    return (status ? rows.filter((r) => r.status === status) : rows).slice().reverse()
  },

  async getSupportRequest(id) {
    requireRole('admin')
    await delay(150)
    const row = mockStore.get().supportRequests.find((r) => r.id === id)
    if (!row) throw new ApiError(404, 'not_found', 'Support request not found')
    return row
  },

  async updateSupportRequestStatus(id, status) {
    requireRole('admin')
    await delay(250)
    let updated: SupportRequest | undefined
    mockStore.update((s) => {
      const row = s.supportRequests.find((r) => r.id === id)
      if (row) {
        row.status = status
        updated = row
      }
    })
    if (!updated) throw new ApiError(404, 'not_found', 'Support request not found')
    return updated
  },

  async createFieldCheck(body) {
    requireRole('field_worker', 'admin')
    await delay(300)
    const row: FieldCheck = { ...body, note: body.note ?? '', id: mockStore.nextId(), created_at: new Date().toISOString() }
    mockStore.update((s) => s.fieldChecks.push(row))
    return row
  },

  async listFieldChecks(cellId) {
    requireRole('field_worker', 'admin')
    await delay(200)
    return mockStore.get().fieldChecks.filter((r) => r.cell_id === cellId)
  },

  async getFacilitiesMap(region: RegionKey) {
    requireRole('citizen', 'admin')
    return mockGeoApi.facilities(region)
  },

  async getAdminTypesMap(region: RegionKey) {
    requireRole('admin')
    return mockGeoApi.types(region)
  },

  async getAdminCandidatesMap(region: RegionKey) {
    requireRole('admin')
    return mockGeoApi.candidates(region)
  },

  async getAdminPlacementsMap(region: RegionKey, radiusM: 1000 | 3000, sites: 3) {
    requireRole('admin')
    return mockGeoApi.placements(region, radiusM, sites)
  },

  async getDemandSignals() {
    requireRole('admin')
    await delay(250)
    // 계약서: facility_id·request_type·status 로 묶고 3건 미만 버킷은 뺀다
    const buckets = new Map<string, DemandSignal>()
    for (const r of mockStore.get().supportRequests) {
      const key = `${r.facility_id}|${r.request_type}|${r.status}`
      const b = buckets.get(key) ?? { facility_id: r.facility_id, request_type: r.request_type, status: r.status, count: 0 }
      b.count += 1
      buckets.set(key, b)
    }
    return [...buckets.values()].filter((b) => b.count >= 3)
  },

  async getFieldFeedbackSummary() {
    requireRole('admin')
    await delay(250)
    const byCell = new Map<string, FieldFeedbackSummary>()
    for (const fc of mockStore.get().fieldChecks) {
      const s = byCell.get(fc.cell_id) ?? { cell_id: fc.cell_id, checked_count: 0, checklist_responses: [] }
      s.checked_count += 1
      // 실제 백엔드처럼 항목 순번(1부터)별 응답 수를 센다
      Object.values(fc.checklist).forEach((_answer, i) => {
        const idx = i + 1
        const item = s.checklist_responses.find((it) => it.item_index === idx) ?? { item_index: idx, response_count: 0 }
        if (!s.checklist_responses.includes(item)) s.checklist_responses.push(item)
        item.response_count += 1
      })
      byCell.set(fc.cell_id, s)
    }
    return [...byCell.values()]
  },

  async publishFieldCheckList(list) {
    requireRole('admin')
    await delay(200)
    mockStore.update((s) => {
      s.fieldCheckList = list
    })
    return { stored: true }
  },

  async fetchFieldCheckList() {
    requireRole('field_worker', 'admin')
    await delay(200)
    return mockStore.get().fieldCheckList
  },
}
