/** 이번 주 일정. 백엔드 API 가 없어 기기(localStorage)에만 둔다. .ics 로 내보낼 수 있다 */
import { useCallback, useEffect, useState } from 'react'
import { downloadTextFile, safeFilename } from '@/lib/download'

export interface ScheduleItem {
  id: string
  facilityId: string
  name: string
  kind: string
  lat: number
  lon: number
  /** ISO 날짜시간 (로컬) */
  when: string
  note?: string
}

const KEY = 'bitamin.citizen.schedule'
const listeners = new Set<() => void>()

function read(): ScheduleItem[] {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as ScheduleItem[]) : []
  } catch {
    return []
  }
}
function write(items: ScheduleItem[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(items))
  } catch {
    /* ignore */
  }
  listeners.forEach((l) => l())
}

export function useSchedule() {
  const [items, setItems] = useState<ScheduleItem[]>(read)
  useEffect(() => {
    const l = () => setItems(read())
    listeners.add(l)
    return () => {
      listeners.delete(l)
    }
  }, [])
  const add = useCallback((item: Omit<ScheduleItem, 'id'>) => {
    const next = [...read(), { ...item, id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}` }]
    next.sort((a, b) => a.when.localeCompare(b.when))
    write(next)
  }, [])
  const remove = useCallback((id: string) => write(read().filter((i) => i.id !== id)), [])
  return { items, add, remove }
}

export const DAY_LABEL = ['일', '월', '화', '수', '목', '금', '토']

export function formatWhen(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const h = d.getHours()
  const ampm = h < 12 ? '오전' : '오후'
  const hh = h % 12 === 0 ? 12 : h % 12
  const mm = d.getMinutes()
  return `${d.getMonth() + 1}월 ${d.getDate()}일 (${DAY_LABEL[d.getDay()]}) ${ampm} ${hh}시${mm ? ` ${mm}분` : ''}`
}

/** 이번 주(일~토) 안의 항목 */
export function isThisWeek(iso: string, now = new Date()): boolean {
  const d = new Date(iso)
  const start = new Date(now)
  start.setHours(0, 0, 0, 0)
  start.setDate(start.getDate() - start.getDay())
  const end = new Date(start)
  end.setDate(end.getDate() + 7)
  return d >= start && d < end
}

function icsDate(iso: string): string {
  const d = new Date(iso)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}T${p(d.getHours())}${p(d.getMinutes())}00`
}

export function downloadIcs(items: ScheduleItem[]) {
  const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//bitamin//citizen schedule//KO']
  for (const i of items) {
    const end = new Date(new Date(i.when).getTime() + 60 * 60 * 1000).toISOString()
    lines.push(
      'BEGIN:VEVENT',
      `UID:${i.id}@bitamin`,
      `DTSTART:${icsDate(i.when)}`,
      `DTEND:${icsDate(end)}`,
      `SUMMARY:${i.name} 방문`,
      `LOCATION:${i.name}`,
      `GEO:${i.lat};${i.lon}`,
      i.note ? `DESCRIPTION:${i.note.replace(/\n/g, '\\n')}` : '',
      'END:VEVENT',
    )
  }
  lines.push('END:VCALENDAR')
  downloadTextFile(`${safeFilename('이번주 일정')}.ics`, lines.filter(Boolean).join('\r\n'), 'text/calendar;charset=utf-8')
}
