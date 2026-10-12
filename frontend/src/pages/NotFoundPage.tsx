import { Link } from 'react-router-dom'
import { EmptyState } from '@/components/ui/EmptyState'

export function NotFoundPage() {
  return (
    <div className="p-8">
      <EmptyState
        title="없는 페이지입니다"
        action={
          <Link to="/" className="font-semibold text-blue-700 underline">
            처음으로
          </Link>
        }
      />
    </div>
  )
}
