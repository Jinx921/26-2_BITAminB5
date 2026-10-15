import { Navigate } from 'react-router-dom'
import { ROLE_HOME } from '@/auth/roleHome'
import { useAuth } from '@/auth/useAuth'
import { Spinner } from '@/components/ui/Spinner'

/** "/" 로 오면 로그인 상태와 역할에 따라 보낸다 */
export function RoleRedirect() {
  const { user, loading } = useAuth()
  if (loading) return <Spinner className="p-8" />
  return <Navigate to={user ? ROLE_HOME[user.role] : '/login'} replace />
}
