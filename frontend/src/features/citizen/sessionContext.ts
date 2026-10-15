import { createContext } from 'react'
import type { QuestionLocation } from '@/types/api'
import type { Display, FacilitiesPoint } from '@/types/display'

export interface LocationChoice extends QuestionLocation {
  /** 사람에게 보여줄 이름: "지금 있는 곳", 주소, "지도에서 고른 곳" */
  label: string
  source: 'gps' | 'map' | 'address'
}

export interface CitizenSession {
  location: LocationChoice | null
  setLocation: (l: LocationChoice | null) => void
  question: string
  setQuestion: (q: string) => void
  answer: Display | null
  setAnswer: (d: Display | null) => void
  /** 마지막 답변의 시설 목록 */
  places: FacilitiesPoint[]
  findPlace: (id: string) => FacilitiesPoint | undefined
}

export const CitizenSessionContext = createContext<CitizenSession | null>(null)
