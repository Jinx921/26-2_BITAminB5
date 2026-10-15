import type { FieldCheckList } from '@/types/api'

const STORAGE_KEY = 'bitamin.fieldCheckList.imported'

export function readImportedFieldCheckList(): FieldCheckList | null {
  const raw = sessionStorage.getItem(STORAGE_KEY)
  if (!raw) return null

  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch {
    throw new Error('가져온 현장 확인 목록을 읽을 수 없습니다. JSON 파일을 다시 불러와 주세요.')
  }
  if (!parsed || typeof parsed !== 'object' || !Array.isArray((parsed as FieldCheckList).cells)) {
    throw new Error('가져온 현장 확인 목록 형식이 올바르지 않습니다.')
  }
  return parsed as FieldCheckList
}

export function saveImportedFieldCheckList(list: FieldCheckList): void {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(list))
}
