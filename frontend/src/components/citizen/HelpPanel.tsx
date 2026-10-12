import { Link } from 'react-router-dom'
import { buttonClass } from '@/components/ui/buttonClass'

/** "혼자 가기 어려우세요?" 옅은 파랑 패널. 함께 갈 이웃 찾기(채움) / 이동 도움 요청(외곽선) */
export function HelpPanel({ facilityId, facilityName }: { facilityId: string | null; facilityName?: string }) {
  const to = (type: 'companion' | 'mobility') => (facilityId ? `/citizen/help/${encodeURIComponent(facilityId)}?type=${type}` : '/citizen/places')
  return (
    <section className="rounded-card border border-primary-line bg-primary-soft p-4">
      <h2 className="text-lg font-bold text-primary-strong">혼자 가기 어려우세요?</h2>
      <p className="mt-1 text-sm text-ink-2">담당자가 같은 곳에 가는 이웃과 함께 가도록 연결해 드려요.{facilityName && ` (${facilityName})`}</p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <div>
          <Link to={to('companion')} className={`${buttonClass('fill', 'md')} w-full whitespace-nowrap px-2 text-[15px]`}>
            함께 갈 이웃 찾기
          </Link>
          <p className="mt-1 text-center text-xs text-ink-3">담당자가 확인 후 연결해요</p>
        </div>
        <div>
          <Link to={to('mobility')} className={`${buttonClass('outline', 'md')} w-full whitespace-nowrap border-primary px-2 text-[15px] text-primary`}>
            이동 도움 요청
          </Link>
          <p className="mt-1 text-center text-xs text-ink-3">담당자에게 전달돼요</p>
        </div>
      </div>
    </section>
  )
}
