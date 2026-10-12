import { Navigate, Outlet, useLocation } from 'react-router-dom'
import type { Role } from '@/types/api'
import { Spinner } from '@/components/ui/Spinner'
import { ROLE_HOME } from './roleHome'
import { useAuth } from './useAuth'

/**
 * 라우트 가드. 로그인 안 했으면 /login 으로, 역할이 맞지 않으면 그 역할의 첫 화면으로 보낸다.
 * 권한 없는 화면은 렌더링 자체를 하지 않는다.
 */
export function RequireRole({ roles }: { roles: Role[] }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner label="확인 중" />
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (!roles.includes(user.role)) return <Navigate to={ROLE_HOME[user.role]} replace />
  return <Outlet />
}
