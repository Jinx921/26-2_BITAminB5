/**
 * 백엔드 날짜 문자열 → 화면 표시.
 * SQLite created_at 은 "2026-10-12 12:14:28" (UTC, 시간대 없음) 형식이라 그대로 new Date() 에 넣으면 브라우저마다 다르게 해석된다.
 */
export function parseServerDate(value: string | null | undefined): Date | null {
  if (!value) return null
  let v = value.trim()
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?$/.test(v)) v = v.replace(' ', 'T') + 'Z'
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? null : d
}

export function formatDateTime(value: string | null | undefined): string {
  const d = parseServerDate(value)
  return d ? d.toLocaleString('ko-KR', { dateStyle: 'short', timeStyle: 'short' }) : (value ?? '')
}
