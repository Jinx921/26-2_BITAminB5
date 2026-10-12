import { AppShell } from './AppShell'

export function FieldLayout() {
  return <AppShell title="현장 확인" variant="mobile" nav={[{ to: '/field', label: '확인 목록', end: true }]} />
}
