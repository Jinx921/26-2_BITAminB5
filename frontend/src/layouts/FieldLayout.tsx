import { Outlet } from 'react-router-dom'
import { ClipboardList } from 'lucide-react'
import { HeaderActions } from '@/components/ui/HeaderActions'
import { MockBadge } from '@/components/ui/MockBadge'
import { COLUMN_WIDTH, useViewMode } from '@/features/viewMode'

/** 현장: 시민과 같은 컬럼 규칙 (모바일 430px / PC 1040px) */
export function FieldLayout() {
  const [mode] = useViewMode()
  return (
    <div className="min-h-full bg-canvas">
      <div className={`relative mx-auto min-h-dvh w-full bg-surface px-4 pb-28 shadow-[0_0_0_1px_var(--color-line)] ${COLUMN_WIDTH[mode]} ${mode === 'desktop' ? 'md:px-8' : ''}`} data-view={mode}>
        <header className="flex items-center justify-between py-3">
          <h1 className="flex items-center gap-2 text-xl font-bold text-ink">
            <ClipboardList className="size-5 text-primary" aria-hidden />
            현장 확인 <MockBadge />
          </h1>
          <HeaderActions />
        </header>
        <Outlet />
      </div>
    </div>
  )
}
