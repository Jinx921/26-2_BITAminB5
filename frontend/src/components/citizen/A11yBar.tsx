import { Button } from '@/components/ui/Button'
import { useBigText, useSpeak } from '@/features/citizen/a11y'

/** 큰 글씨 전환 + 읽어주기. 시민 화면 상단에 항상 둔다 */
export function A11yBar({ textToRead }: { textToRead?: string }) {
  const [big, toggleBig] = useBigText()
  const { speak, stop, speaking, supported } = useSpeak()
  return (
    <div className="flex flex-wrap gap-2">
      <Button variant="secondary" size="lg" onClick={toggleBig} aria-pressed={big}>
        {big ? '글씨 보통으로' : '글씨 크게'}
      </Button>
      {supported && textToRead && (
        <Button variant="secondary" size="lg" onClick={() => (speaking ? stop() : speak(textToRead))} aria-pressed={speaking}>
          {speaking ? '읽기 멈추기' : '읽어주기'}
        </Button>
      )}
    </div>
  )
}
