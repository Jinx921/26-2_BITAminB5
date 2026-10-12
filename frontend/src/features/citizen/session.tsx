import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { CitizenSessionContext, type LocationChoice } from './sessionContext'
export type { LocationChoice, CitizenSession } from './sessionContext'
import type { Display, FacilitiesPoint } from '@/types/display'

/**
 * 시민 화면끼리 공유하는 상태.
 * - 찾을 위치는 개인정보(가족 집 주소일 수 있음)라 메모리에만 두고 저장하지 않는다 (agent/README 7절).
 * - 마지막 답변은 탭을 옮겨도 보이도록 sessionStorage 에 둔다 (위치는 들어 있지 않다).
 */


const Ctx = CitizenSessionContext
const ANSWER_KEY = 'bitamin.citizen.answer'

function readAnswer(): Display | null {
  try {
    const raw = sessionStorage.getItem(ANSWER_KEY)
    return raw ? (JSON.parse(raw) as Display) : null
  } catch {
    return null
  }
}

export function CitizenSessionProvider({ children }: { children: ReactNode }) {
  const [location, setLocation] = useState<LocationChoice | null>(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswerState] = useState<Display | null>(readAnswer)

  const setAnswer = useCallback((d: Display | null) => {
    setAnswerState(d)
    try {
      if (d) sessionStorage.setItem(ANSWER_KEY, JSON.stringify(d))
      else sessionStorage.removeItem(ANSWER_KEY)
    } catch {
      /* ignore */
    }
  }, [])

  const places = useMemo<FacilitiesPoint[]>(() => (answer?.map?.layer === 'facilities' ? answer.map.points : []), [answer])
  const findPlace = useCallback((id: string) => places.find((p) => p.id === id), [places])

  const value = useMemo(
    () => ({ location, setLocation, question, setQuestion, answer, setAnswer, places, findPlace }),
    [location, question, answer, setAnswer, places, findPlace],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
