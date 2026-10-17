/**
 * 목업 저장소. 같은 브라우저의 관리자·시민·현장 화면이 데이터를 공유하도록 localStorage 에 둔다.
 * 실제 백엔드의 SQLite 역할이다.
 */
import type { FieldCheck, FieldCheckList, SupportRequest } from '@/types/api'

const KEY = 'bitamin.mock.store.v1'

interface MockState {
  /** 화면에서 가입한 시민 계정 (목업 전용) */
  users: { id: number; email: string; password: string; created_at: string }[]
  supportRequests: SupportRequest[]
  fieldChecks: FieldCheck[]
  fieldCheckList: FieldCheckList | null
  fieldCheckLists: Record<number, FieldCheckList>
  nextId: number
}

const initial: MockState = { users: [], supportRequests: [], fieldChecks: [], fieldCheckList: null, fieldCheckLists: {}, nextId: 1 }

function load(): MockState {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return structuredClone(initial)
    return { ...structuredClone(initial), ...(JSON.parse(raw) as Partial<MockState>) }
  } catch {
    return structuredClone(initial)
  }
}

function save(current: MockState) {
  try {
    localStorage.setItem(KEY, JSON.stringify(current))
  } catch {
    /* ignore */
  }
}

let state: MockState | null = null

function currentState(): MockState {
  state ??= load()
  return state
}

export const mockStore = {
  get: currentState,
  update(fn: (s: MockState) => void) {
    const current = currentState()
    fn(current)
    save(current)
  },
  nextId() {
    const current = currentState()
    const id = current.nextId++
    save(current)
    return id
  },
  reset() {
    state = structuredClone(initial)
    save(state)
  },
}
