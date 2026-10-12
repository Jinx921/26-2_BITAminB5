import { Outlet } from 'react-router-dom'
import { ClipboardList } from 'lucide-react'
import { useAuth } from '@/auth/useAuth'
import { Menu } from '@/components/ui/Menu'
import { MockBadge } from '@/components/ui/MockBadge'

/** 현장: 시민과 같은 430px 단일 컬럼 */
export function FieldLayout() {
  const { user, logout } = useAuth()
  return (
    <div className="min-h-full bg-canvas">
      <div className="relative mx-auto min-h-dvh w-full max-w-[430px] bg-surface px-4 pb-28 shadow-[0_0_0_1px_var(--color-line)]">
        <header className="flex items-center justify-between py-3">
          <h1 className="flex items-center gap-2 text-xl font-bold text-ink">
            <ClipboardList className="size-5 text-primary" aria-hidden />
            현장 확인 <MockBadge />
          </h1>
          <Menu header={user?.email} items={[{ label: '로그아웃', onSelect: logout, danger: true }]} />
        </header>
        <Outlet />
      </div>
    </div>
  )
}
