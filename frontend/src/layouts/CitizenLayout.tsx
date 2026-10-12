import { Outlet } from 'react-router-dom'
import { CitizenSessionProvider } from '@/features/citizen/session'
import { COLUMN_WIDTH, useViewMode } from '@/features/viewMode'

/** 시민: 모바일은 430px 단일 컬럼, PC 보기는 1040px. 바깥은 옅은 회색, 컬럼은 흰색 */
export function CitizenLayout() {
  const [mode] = useViewMode()
  return (
    <CitizenSessionProvider>
      <div className="min-h-full bg-canvas">
        <div className={`relative mx-auto min-h-dvh w-full bg-surface px-4 pb-28 shadow-[0_0_0_1px_var(--color-line)] ${COLUMN_WIDTH[mode]} ${mode === 'desktop' ? 'md:px-8' : ''}`} data-view={mode}>
          <Outlet />
        </div>
      </div>
    </CitizenSessionProvider>
  )
}
