import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from '@/api'
import { setUnauthorizedHandler, tokenStore } from '@/api/client'
import type { User } from '@/types/api'
import { AuthContext, type AuthState } from './AuthContext'

const USER_KEY = 'bitamin.auth.user'

function readUser(): User | null {
  try {
    const raw = sessionStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}

function writeUser(user: User | null) {
  try {
    if (user) sessionStorage.setItem(USER_KEY, JSON.stringify(user))
    else sessionStorage.removeItem(USER_KEY)
  } catch {
    /* ignore */
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  // 새로고침 시 세션 복구. 토큰이 만료됐으면 사용자도 지운다 (동기라 loading 은 항상 false)
  const [user, setUser] = useState<User | null>(() => {
    const stored = tokenStore.get()
    if (!stored) writeUser(null)
    return stored ? readUser() : null
  })
  const loading = false

  const logout = useCallback(() => {
    tokenStore.clear()
    writeUser(null)
    setUser(null)
  }, [])

  // API 가 401 을 받으면 로그아웃 상태로 돌린다 (RequireRole 이 로그인 화면으로 보낸다)
  useEffect(() => {
    setUnauthorizedHandler(logout)
    return () => setUnauthorizedHandler(null)
  }, [logout])

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.login(email, password)
    // 만료 1분 전에 버리도록 여유를 둔다
    tokenStore.set({ token: res.access_token, expiresAt: Date.now() + Math.max(res.expires_in - 60, 30) * 1000 })
    writeUser(res.user)
    setUser(res.user)
    return res.user
  }, [])

  const value = useMemo<AuthState>(() => ({ user, loading, login, logout }), [user, loading, login, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
