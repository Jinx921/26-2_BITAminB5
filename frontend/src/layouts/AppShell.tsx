import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '@/auth/useAuth'
import { ROLE_LABEL } from '@/auth/roleHome'
import { Button } from '@/components/ui/Button'
import { MockBadge } from '@/components/ui/MockBadge'

export interface NavItem {
  to: string
  label: string
  end?: boolean
}

/**
 * 공통 껍데기. 관리자는 상단 메뉴, 시민·현장은 모바일 우선이라 하단 탭으로 보인다.
 */
export function AppShell({ title, nav, variant }: { title: string; nav: NavItem[]; variant: 'desktop' | 'mobile' }) {
  const { user, logout } = useAuth()
  const isMobile = variant === 'mobile'

  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold">{title}</span>
            <MockBadge />
          </div>
          {!isMobile && (
            <nav className="flex gap-1" aria-label="주 메뉴">
              {nav.map((n) => (
                <NavLink
                  key={n.to}
                  to={n.to}
                  end={n.end}
                  className={({ isActive }) =>
                    `rounded-lg px-3 py-2 font-medium ${isActive ? 'bg-blue-50 text-blue-800' : 'text-slate-700 hover:bg-slate-100'}`
                  }
                >
                  {n.label}
                </NavLink>
              ))}
            </nav>
          )}
          <div className="flex items-center gap-2 text-sm text-slate-600">
            {user && (
              <span className="hidden sm:inline">
                {ROLE_LABEL[user.role]} · {user.email}
              </span>
            )}
            <Button variant="ghost" size="md" onClick={logout}>
              로그아웃
            </Button>
          </div>
        </div>
      </header>

      <main className={`mx-auto w-full max-w-6xl flex-1 px-4 py-6 ${isMobile ? 'pb-24' : ''}`}>
        <Outlet />
      </main>

      {isMobile && (
        <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-200 bg-white" aria-label="하단 메뉴">
          <div className="mx-auto grid max-w-6xl auto-cols-fr grid-flow-col">
            {nav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  `flex min-h-16 items-center justify-center px-2 text-center text-base font-semibold ${isActive ? 'text-blue-800' : 'text-slate-600'}`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </div>
        </nav>
      )}
    </div>
  )
}
