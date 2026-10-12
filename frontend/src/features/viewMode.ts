/** 시민·현장 화면의 모바일/PC 보기 전환. 기기 localStorage 에 기억한다 */
import { useCallback, useEffect, useState } from 'react'

export type ViewMode = 'mobile' | 'desktop'
const KEY = 'bitamin.viewMode'
const listeners = new Set<() => void>()

function read(): ViewMode {
  try {
    return localStorage.getItem(KEY) === 'desktop' ? 'desktop' : 'mobile'
  } catch {
    return 'mobile'
  }
}

export function useViewMode(): [ViewMode, () => void] {
  const [mode, setMode] = useState<ViewMode>(read)
  useEffect(() => {
    const l = () => setMode(read())
    listeners.add(l)
    return () => {
      listeners.delete(l)
    }
  }, [])
  const toggle = useCallback(() => {
    const next: ViewMode = read() === 'desktop' ? 'mobile' : 'desktop'
    try {
      localStorage.setItem(KEY, next)
    } catch {
      /* ignore */
    }
    listeners.forEach((l) => l())
  }, [])
  return [mode, toggle]
}

/** 컬럼 최대 폭 클래스 */
export const COLUMN_WIDTH: Record<ViewMode, string> = { mobile: 'max-w-[430px]', desktop: 'max-w-[1040px]' }
