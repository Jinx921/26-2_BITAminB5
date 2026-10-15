import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { describeError, isMockMode } from '@/api'
import { DEMO_ACCOUNTS } from '@/api/mock/accounts'
import { ROLE_HOME } from '@/auth/roleHome'
import { useAuth } from '@/auth/useAuth'
import { Button } from '@/components/ui/Button'
import { MockBadge } from '@/components/ui/MockBadge'
import type { Role } from '@/types/api'

const input = 'w-full rounded-btn border border-line-strong px-3 py-3 text-base focus:border-primary focus:outline-none'

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
      navigate(from && isAllowed(from, u.role) ? from : ROLE_HOME[u.role], { replace: true })
    } catch (err) {
      setError(describeError(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center bg-canvas px-4 py-10">
      <div className="w-full max-w-sm rounded-card border border-line bg-surface p-8">
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">우리 동네 함께 <MockBadge /></h1>
        <p className="mt-1 text-sm text-ink-3">관리자, 현장 담당자, 시민 계정으로 들어갑니다.</p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <label className="block">
            <span className="mb-1 block text-sm font-semibold text-ink-2">이메일</span>
            <input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} className={input} />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-semibold text-ink-2">비밀번호</span>
            <input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} className={input} />
          </label>
          {error && <p role="alert" className="text-sm text-danger">{error}</p>}
          <Button type="submit" size="lg" className="w-full" loading={busy}>로그인</Button>
        </form>
        {isMockMode ? (
          <p className="mt-6 text-center text-sm text-ink-3">
            데모로 들어가기:{' '}
            {DEMO_ACCOUNTS.map((a, i) => (
              <span key={a.email}>
                {i > 0 && ' · '}
                <button type="button" disabled={busy} onClick={() => submit(undefined, a)} className="font-semibold text-primary underline-offset-2 hover:underline">
                  {a.label}
                </button>
              </span>
            ))}
          </p>
        ) : (
          <p className="mt-6 text-center text-xs text-ink-3">시민 계정은 가입 API 로, 관리자·현장 계정은 backend/seed_user.py 로 만듭니다.</p>
        )}
      </div>
    </div>
  )
}

function isAllowed(path: string, role: Role): boolean {
  if (path.startsWith('/admin')) return role === 'admin'
  if (path.startsWith('/citizen')) return role === 'citizen'
  if (path.startsWith('/field')) return role === 'field_worker' || role === 'admin'
  return true
}
