import { describeError } from '@/api/client'
import { Button } from './Button'

export function ErrorState({ error, onRetry, title = '문제가 생겼습니다' }: { error: unknown; onRetry?: () => void; title?: string }) {
  return (
    <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-6">
      <p className="text-lg font-semibold text-red-800">{title}</p>
      <p className="mt-1 text-red-700">{describeError(error)}</p>
      {onRetry && (
        <Button variant="secondary" className="mt-4" onClick={onRetry}>
          다시 시도
        </Button>
      )}
    </div>
  )
}
