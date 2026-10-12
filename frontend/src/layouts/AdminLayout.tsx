import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '@/auth/useAuth'
import { Menu } from '@/components/ui/Menu'
import { MockBadge } from '@/components/ui/MockBadge'

const NAV = [
  { to: '/admin', label: '지도와 질문', end: true },
  { to: '/admin/requests', label: '시민 요청' },
  { to: '/admin/field-list', label: '현장 확인 목록' },
]

/** 관리자: 얇은 상단 탭 바 + 화면 높이를 채우는 본문 */
export function AdminLayout() {
  const { user, logout } = useAuth()
  return (
    <div className="flex h-dvh flex-col bg-surface">
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-line px-4">
        <div className="flex items-center gap-6">
          <span className="flex items-center gap-2 text-base font-bold text-ink">
            관리자 <MockBadge />
          </span>
          <nav className="flex h-12 gap-1" aria-label="주 메뉴">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => `inline-flex items-center border-b-2 px-2 text-sm font-semibold ${isActive ? 'border-primary text-primary' : 'border-transparent text-ink-2 hover:text-ink'}`}>
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
        <Menu header={user?.email} items={[{ label: '로그아웃', onSelect: logout, danger: true }]} />
      </header>
      <main className="min-h-0 flex-1">
        <Outlet />
      </main>
    </div>
  )
}
