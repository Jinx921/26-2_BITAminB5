import { LogOut, Monitor, Smartphone } from 'lucide-react'
import { useAuth } from '@/auth/useAuth'
import { useViewMode } from '@/features/viewMode'
import { Button } from './Button'

/** 모바일/PC 전환 + 로그아웃. 시민·현장 화면 상단에 둔다 */
export function HeaderActions({ withViewToggle = true }: { withViewToggle?: boolean }) {
  const { logout } = useAuth()
  const [mode, toggle] = useViewMode()
  return (
    <div className="flex shrink-0 items-center gap-1">
      {withViewToggle && (
        <span className="hidden sm:inline-flex">
          <Button variant="text" size="sm" className="whitespace-nowrap px-2 text-ink-2" onClick={toggle} icon={mode === 'desktop' ? <Smartphone className="size-4" /> : <Monitor className="size-4" />} title={mode === 'desktop' ? '모바일 화면으로 보기' : 'PC 화면으로 보기'}>
            {mode === 'desktop' ? '모바일 화면' : 'PC 화면'}
          </Button>
        </span>
      )}
      <Button variant="text" size="sm" className="whitespace-nowrap px-2 text-ink-2" onClick={logout} icon={<LogOut className="size-4" />}>
        로그아웃
      </Button>
    </div>
  )
}
