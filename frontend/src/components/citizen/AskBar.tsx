import { useCallback, type FormEvent } from 'react'
import { Mic, MicOff, SendHorizonal } from 'lucide-react'
import { useSpeechInput } from '@/features/citizen/a11y'
import { COLUMN_WIDTH, useViewMode } from '@/features/viewMode'

export interface AskBarProps {
  value: string
  onChange: (v: string) => void
  onSubmit: (q: string, viaVoice: boolean) => void
  pending: boolean
}

/** 화면 하단 고정 한 줄 입력 바. 마이크는 입력창 안 아이콘 */
export function AskBar({ value, onChange, onSubmit, pending }: AskBarProps) {
  const [mode] = useViewMode()
  const speech = useSpeechInput(
    useCallback(
      (t: string) => {
        onChange(t)
        onSubmit(t, true)
      },
      [onChange, onSubmit],
    ),
  )

  function submit(e: FormEvent) {
    e.preventDefault()
    const q = value.trim()
    if (!q || pending) return
    onSubmit(q, false)
  }

  return (
    <div data-fixed-bar className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-surface/95 backdrop-blur">
      <form onSubmit={submit} className={`mx-auto flex items-center gap-2 px-4 py-2 pb-[calc(0.5rem+env(safe-area-inset-bottom))] ${COLUMN_WIDTH[mode]}`}>
        <div className="relative min-w-0 flex-1">
          <input
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={speech.listening ? '듣고 있어요…' : '궁금한 걸 물어보세요'}
            aria-label="질문"
            disabled={pending}
            className="w-full rounded-full border border-line-strong bg-surface py-3 pl-4 pr-12 text-base focus:border-primary focus:outline-none"
          />
          {speech.supported && (
            <button
              type="button"
              onClick={() => (speech.listening ? speech.stop() : speech.start())}
              aria-label={speech.listening ? '말하기 멈추기' : '말로 물어보기'}
              aria-pressed={speech.listening}
              className={`absolute right-1 top-1/2 inline-flex size-10 -translate-y-1/2 items-center justify-center rounded-full ${speech.listening ? 'bg-danger text-white' : 'text-ink-2 hover:bg-canvas'}`}
            >
              {speech.listening ? <MicOff className="size-5" /> : <Mic className="size-5" />}
            </button>
          )}
        </div>
        <button type="submit" disabled={!value.trim() || pending} aria-label="물어보기" className="inline-flex size-11 shrink-0 items-center justify-center rounded-full bg-primary text-white disabled:bg-primary/40">
          <SendHorizonal className="size-5" />
        </button>
      </form>
      {speech.error && <p className={`mx-auto px-4 pb-2 text-sm text-amber-ink ${COLUMN_WIDTH[mode]}`}>{speech.error}</p>}
    </div>
  )
}
