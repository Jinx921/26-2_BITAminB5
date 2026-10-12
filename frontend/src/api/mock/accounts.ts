/** 목업 전용 데모 계정. 실제 모드에서는 쓰이지 않는다 (비밀번호 12자 이상, 이메일은 백엔드 검증기가 받는 도메인). */
import type { Role, User } from '@/types/api'

export interface DemoAccount {
  email: string
  password: string
  role: Role
  label: string
}

export const DEMO_ACCOUNTS: DemoAccount[] = [
  { email: 'admin@example.com', password: 'demo-admin-1234', role: 'admin', label: '관리자' },
  { email: 'citizen@example.com', password: 'demo-citizen-1234', role: 'citizen', label: '시민' },
  { email: 'field@example.com', password: 'demo-field-1234', role: 'field_worker', label: '현장 담당자' },
]

export function demoUser(a: DemoAccount, id: number): User {
  return { id, email: a.email, role: a.role, created_at: '2026-10-01T00:00:00+09:00' }
}

/** 목업 토큰에서 역할을 읽는다 */
export function roleFromMockToken(token: string | null | undefined): Role | null {
  if (!token?.startsWith('mock.')) return null
  const role = token.split('.')[1]
  return role === 'admin' || role === 'citizen' || role === 'field_worker' ? role : null
}
