import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { describeError, isMockMode } from '@/api'
import { DEMO_ACCOUNTS } from '@/api/mock/accounts'
import { ROLE_HOME } from '@/auth/roleHome'
import { useAuth } from '@/auth/useAuth'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { MockBadge } from '@/components/ui/MockBadge'
import type { Role } from '@/types/api'

export function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={ROLE_HOME[user.role]} replace />

  const from = (location.state as { from?: string } | null)?.from

  async function submit(e?: FormEvent, creds?: { email: string; password: string }) {
    e?.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const u = await login(creds?.email ?? email, creds?.password ?? password)
      const target = from && isAllowed(from, u.role) ? from : ROLE_HOME[u.role]
      navigate(target, { replace: true })
    } catch (err) {
      setError(describeError(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center px-4 py-10">
      <Card className="w-full max-w-md p-6">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold">동네 돌봄 지도</h1>
          <MockBadge />
        </div>
        <form onSubmit={submit} className="space-y-4">
          <label className="block">
            <span className="mb-1 block font-medium">이메일</span>
            <input
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-3 text-lg"
            />
          </label>
          <label className="block">
            <span className="mb-1 block font-medium">비밀번호</span>
            <input
              type="password"
              autoComplete="current-password"
              required
              minLength={1}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-3 text-lg"
            />
          </label>
          {error && (
            <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-red-700">
              {error}
            </p>
          )}
          <Button type="submit" size="lg" className="w-full" loading={busy}>
            로그인
          </Button>
        </form>

        {isMockMode && (
          <div className="mt-6 border-t border-slate-200 pt-4">
            <p className="mb-2 text-sm text-slate-600">목업 모드 데모 계정 (클릭하면 바로 로그인)</p>
            <div className="grid gap-2">
              {DEMO_ACCOUNTS.map((a) => (
                <Button key={a.email} variant="secondary" disabled={busy} onClick={() => submit(undefined, a)}>
                  {a.label}로 들어가기
                </Button>
              ))}
            </div>
          </div>
        )}
        {!isMockMode && (
          <p className="mt-6 text-sm text-slate-500">
            시민 계정은 백엔드 /api/v1/auth/register 로 만들고, 관리자·현장 계정은 backend/seed_user.py 로 만듭니다.
          </p>
        )}
      </Card>
    </div>
  )
}

function isAllowed(path: string, role: Role): boolean {
  if (path.startsWith('/admin')) return role === 'admin'
  if (path.startsWith('/citizen')) return role === 'citizen'
  if (path.startsWith('/field')) return role === 'field_worker' || role === 'admin'
  return true
}
