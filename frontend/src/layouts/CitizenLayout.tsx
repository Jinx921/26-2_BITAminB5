import { AppShell } from './AppShell'

export function CitizenLayout() {
  return (
    <AppShell
      title="우리 동네"
      variant="mobile"
      nav={[
        { to: '/citizen', label: '물어보기', end: true },
        { to: '/citizen/places', label: '갈 곳' },
        { to: '/citizen/schedule', label: '이번 주' },
      ]}
    />
  )
}
