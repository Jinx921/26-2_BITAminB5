import type { ReactNode } from 'react'
import { Volume2, VolumeX } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { HeaderActions } from '@/components/ui/HeaderActions'
import { MockBadge } from '@/components/ui/MockBadge'
import { useBigText, useSpeak } from '@/features/citizen/a11y'

/** 1줄: 제목 + 큰 글씨(채움)·읽어주기(외곽선) 알약 / 2줄: 위치 등 부제 + PC 전환·로그아웃 */
export function CitizenHeader({ textToRead, subtitle }: { textToRead?: string; subtitle?: ReactNode }) {
  const [big, toggleBig] = useBigText()
  const { speak, stop, speaking, supported } = useSpeak()
  return (
    <header className="pt-2">
      <div className="flex items-center justify-between gap-2">
        <h1 className="flex items-center gap-2 whitespace-nowrap text-2xl font-bold tracking-tight text-ink">
          우리 동네 함께 <MockBadge />
        </h1>
        <div className="flex shrink-0 items-center gap-1.5">
          <Button size="sm" pill variant="fill" onClick={toggleBig} aria-pressed={big} className="whitespace-nowrap px-3 text-[13px]">
            가+ 큰 글씨
          </Button>
          {supported && (
            <Button size="sm" pill variant="outline" onClick={() => (speaking ? stop() : textToRead && speak(textToRead))} disabled={!textToRead && !speaking} aria-pressed={speaking} icon={speaking ? <VolumeX className="size-4" /> : <Volume2 className="size-4" />} className="whitespace-nowrap px-3 text-[13px]">
              {speaking ? '멈추기' : '읽어주기'}
            </Button>
          )}
        </div>
      </div>
      <div className="mt-1 flex items-center justify-between gap-2">
        <div className="min-w-0 flex-1">{subtitle}</div>
        <HeaderActions />
      </div>
    </header>
  )
}
