import { AlertCircle } from 'lucide-react'
import { describeError } from '@/api/client'
import { Button } from './Button'

export function ErrorState({ error, onRetry, title = '문제가 생겼습니다' }: { error: unknown; onRetry?: () => void; title?: string }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-card border border-red-200 bg-red-50 p-4">
      <AlertCircle className="mt-0.5 size-5 shrink-0 text-danger" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="font-semibold text-danger">{title}</p>
        <p className="mt-0.5 text-sm text-ink-2">{describeError(error)}</p>
        {onRetry && (
          <Button variant="text" size="sm" className="-ml-3 mt-1" onClick={onRetry}>
            다시 시도
          </Button>
        )}
      </div>
    </div>
  )
}
