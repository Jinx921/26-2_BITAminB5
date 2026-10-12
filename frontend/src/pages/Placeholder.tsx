import { PageHeader } from '@/components/ui/PageHeader'
import { EmptyState } from '@/components/ui/EmptyState'

/** 다음 단계에서 채울 화면 자리 */
export function Placeholder({ title, stage }: { title: string; stage: string }) {
  return (
    <>
      <PageHeader title={title} />
      <EmptyState title="준비 중" description={`${stage}에서 구현합니다.`} />
    </>
  )
}
