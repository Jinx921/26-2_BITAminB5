import type { Role } from '@/types/api'

/** 역할별 첫 화면 */
export const ROLE_HOME: Record<Role, string> = {
  admin: '/admin',
  citizen: '/citizen',
  field_worker: '/field',
}

export const ROLE_LABEL: Record<Role, string> = {
  admin: '관리자',
  citizen: '시민',
  field_worker: '현장 담당자',
}
