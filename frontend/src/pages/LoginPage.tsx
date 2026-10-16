import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { api, describeError, isMockMode } from '@/api'
import { DEMO_ACCOUNTS } from '@/api/mock/accounts'
import { ROLE_HOME } from '@/auth/roleHome'
import { useAuth } from '@/auth/useAuth'
import { Button } from '@/components/ui/Button'
import { MockBadge } from '@/components/ui/MockBadge'
import type { Role } from '@/types/api'

const input = 'w-full rounded-btn border border-line-strong px-3 py-3 text-base focus:border-primary focus:outline-none'
const MIN_PW = 12

/** 로그인 + 시민 가입. 관리자·현장 계정은 운영자가 만들어 주므로 가입은 시민만 */
export function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={ROLE_HOME[user.role]} replace />
  const from = (location.state as { from?: string } | null)?.from

  async function doLogin(creds: { email: string; password: string }) {
    const u = await login(creds.email, creds.password)
    navigate(from && isAllowed(from, u.role) ? from : ROLE_HOME[u.role], { replace: true })
  }

  async function submit(e?: FormEvent, creds?: { email: string; password: string }) {
    e?.preventDefault()
    setError(null)
    if (mode === 'signup' && !creds) {
      if (password.length < MIN_PW) return setError(`비밀번호는 ${MIN_PW}자 이상이어야 해요.`)
      if (password !== confirm) return setError('비밀번호가 서로 달라요.')
    }
    setBusy(true)
    try {
      if (mode === 'signup' && !creds) {
        await api.register(email.trim(), password)
        await doLogin({ email: email.trim(), password })
      } else {
        await doLogin(creds ?? { email, password })
      }
    } catch (err) {
      setError(describeError(err))
    } finally {
      setBusy(false)
    }
  }

  function switchMode(next: 'login' | 'signup') {
    setMode(next)
    setError(null)
    setConfirm('')
  }

  const signup = mode === 'signup'

  return (
    <div className="flex min-h-full items-center justify-center bg-canvas px-4 py-10">
      <div className="w-full max-w-sm rounded-card border border-line bg-surface p-8">
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">우리 동네 함께 <MockBadge /></h1>
        <p className="mt-1 text-sm text-ink-3">{signup ? '시민 계정을 만들어요. 이메일과 비밀번호만 있으면 돼요.' : '관리자, 현장 담당자, 시민 계정으로 들어갑니다.'}</p>

        <form onSubmit={submit} className="mt-6 space-y-4">
          <label className="block">
            <span className="mb-1 block text-sm font-semibold text-ink-2">이메일</span>
            <input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} className={input} />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-semibold text-ink-2">비밀번호{signup && <span className="ml-1 font-normal text-ink-3">({MIN_PW}자 이상)</span>}</span>
            <input type="password" autoComplete={signup ? 'new-password' : 'current-password'} required minLength={signup ? MIN_PW : 1} value={password} onChange={(e) => setPassword(e.target.value)} className={input} />
          </label>
          {signup && (
            <label className="block">
              <span className="mb-1 block text-sm font-semibold text-ink-2">비밀번호 확인</span>
              <input type="password" autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} className={input} />
            </label>
          )}
          {error && <p role="alert" className="text-sm text-danger">{error}</p>}
          <Button type="submit" size="lg" className="w-full" loading={busy}>{signup ? '가입하고 시작하기' : '로그인'}</Button>
        </form>

        <p className="mt-5 text-center text-sm text-ink-3">
          {signup ? (
            <>이미 계정이 있으면 <button type="button" onClick={() => switchMode('login')} className="font-semibold text-primary">로그인</button></>
          ) : (
            <>처음이세요? <button type="button" onClick={() => switchMode('signup')} className="font-semibold text-primary">시민 계정 만들기</button></>
          )}
        </p>
        {!signup && <p className="mt-1 text-center text-xs text-ink-3">관리자·현장 담당자 계정은 운영자에게 받으세요.</p>}

        {isMockMode && !signup && (
          <p className="mt-5 border-t border-line pt-4 text-center text-sm text-ink-3">
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
