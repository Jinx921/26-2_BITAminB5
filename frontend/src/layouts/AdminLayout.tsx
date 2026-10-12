import { AppShell } from './AppShell'

export function AdminLayout() {
  return (
    <AppShell
      title="관리자"
      variant="desktop"
      nav={[
        { to: '/admin', label: '지도와 질문', end: true },
        { to: '/admin/requests', label: '시민 요청' },
        { to: '/admin/field-list', label: '현장 확인 목록' },
      ]}
    />
  )
}
