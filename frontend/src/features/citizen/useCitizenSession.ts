import { useContext } from 'react'
import { CitizenSessionContext, type CitizenSession } from './sessionContext'

export function useCitizenSession(): CitizenSession {
  const v = useContext(CitizenSessionContext)
  if (!v) throw new Error('useCitizenSession 은 CitizenSessionProvider 안에서만 쓸 수 있다')
  return v
}
