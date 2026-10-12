/** 이 기기에서 저장을 마친 동네 표시 (목록 화면의 체크 표시용) */
import { useCallback, useEffect, useState } from 'react'

const KEY = 'bitamin.field.done'
const listeners = new Set<() => void>()

function read(): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '{}') as Record<string, string>
  } catch {
    return {}
  }
}

export function useDoneCells() {
  const [done, setDone] = useState(read)
  useEffect(() => {
    const l = () => setDone(read())
    listeners.add(l)
    return () => {
      listeners.delete(l)
    }
  }, [])
  const markDone = useCallback((cellId: string) => {
    const next = { ...read(), [cellId]: new Date().toISOString() }
    try {
      localStorage.setItem(KEY, JSON.stringify(next))
    } catch {
      /* ignore */
    }
    listeners.forEach((l) => l())
  }, [])
  return { done, markDone }
}
