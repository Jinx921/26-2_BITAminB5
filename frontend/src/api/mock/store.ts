/**
 * 목업 저장소. 같은 브라우저의 관리자·시민·현장 화면이 데이터를 공유하도록 localStorage 에 둔다.
 * 실제 백엔드의 SQLite 역할이다.
 */
import type { FieldCheck, FieldCheckList, SupportRequest } from '@/types/api'

const KEY = 'bitamin.mock.store.v1'

interface MockState {
  supportRequests: SupportRequest[]
  fieldChecks: FieldCheck[]
  fieldCheckList: FieldCheckList | null
  nextId: number
}

const initial: MockState = { supportRequests: [], fieldChecks: [], fieldCheckList: null, nextId: 1 }

function load(): MockState {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return structuredClone(initial)
    return { ...structuredClone(initial), ...(JSON.parse(raw) as Partial<MockState>) }
  } catch {
    return structuredClone(initial)
  }
}

let state: MockState = load()

function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify(state))
  } catch {
    /* ignore */
  }
}

export const mockStore = {
  get: () => state,
  update(fn: (s: MockState) => void) {
    fn(state)
    save()
  },
  nextId() {
    const id = state.nextId++
    save()
    return id
  },
  reset() {
    state = structuredClone(initial)
    save()
  },
}
