import { createContext } from 'react'
import type { User } from '@/types/api'

export interface AuthState {
  user: User | null
  /** 세션에 토큰이 있는지 확인하는 중 (첫 렌더) */
  loading: boolean
  login(email: string, password: string): Promise<User>
  logout(): void
}

export const AuthContext = createContext<AuthState | null>(null)
