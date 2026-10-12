import { Outlet } from 'react-router-dom'
import { CitizenSessionProvider } from '@/features/citizen/session'

/** 시민: 최대 430px 단일 컬럼, 바깥은 옅은 회색, 컬럼은 흰색 */
export function CitizenLayout() {
  return (
    <CitizenSessionProvider>
      <div className="min-h-full bg-canvas">
        <div className="relative mx-auto min-h-dvh w-full max-w-[430px] bg-surface px-4 pb-28 shadow-[0_0_0_1px_var(--color-line)]">
          <Outlet />
        </div>
      </div>
    </CitizenSessionProvider>
  )
}
