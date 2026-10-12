import { Volume2, VolumeX } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Menu } from '@/components/ui/Menu'
import { MockBadge } from '@/components/ui/MockBadge'
import { useAuth } from '@/auth/useAuth'
import { useBigText, useSpeak } from '@/features/citizen/a11y'

/** 제목 + 큰 글씨(채움)·읽어주기(외곽선) 알약 + 메뉴(로그아웃) */
export function CitizenHeader({ textToRead, subtitle }: { textToRead?: string; subtitle?: React.ReactNode }) {
  const [big, toggleBig] = useBigText()
  const { speak, stop, speaking, supported } = useSpeak()
  const { user, logout } = useAuth()
  return (
    <header className="pt-2">
      <div className="flex items-center justify-between gap-2">
        <h1 className="whitespace-nowrap text-2xl font-bold tracking-tight text-ink">우리 동네 함께</h1>
        <div className="flex shrink-0 items-center gap-1.5">
          <Button size="sm" pill variant="fill" onClick={toggleBig} aria-pressed={big} className="whitespace-nowrap px-3 text-[13px]">
            가+ 큰 글씨
          </Button>
          {supported && (
            <Button size="sm" pill variant="outline" onClick={() => (speaking ? stop() : textToRead && speak(textToRead))} disabled={!textToRead && !speaking} aria-pressed={speaking} icon={speaking ? <VolumeX className="size-4" /> : <Volume2 className="size-4" />} className="whitespace-nowrap px-3 text-[13px]">
              {speaking ? '멈추기' : '읽어주기'}
            </Button>
          )}
          <Menu label="메뉴" header={<span className="flex items-center gap-2">{user?.email} <MockBadge /></span>} items={[{ label: '로그아웃', onSelect: logout, danger: true }]} />
        </div>
      </div>
      {subtitle && <div className="mt-1">{subtitle}</div>}
    </header>
  )
}
