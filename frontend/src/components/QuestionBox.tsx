import { useEffect, useState, type FormEvent } from 'react'
import { SendHorizonal } from 'lucide-react'
import { QUESTION_WAIT_HINT_SECONDS } from '@/config'

export interface QuestionBoxProps {
  onSubmit: (question: string) => void
  pending: boolean
  placeholder?: string
  samples?: string[]
  value?: string
  onChange?: (v: string) => void
}

/** 관리자 질문 입력. 답이 15~35초 걸리므로 경과 시간을 보여준다 */
export function QuestionBox({ onSubmit, pending, placeholder, samples, value, onChange }: QuestionBoxProps) {
  const [inner, setInner] = useState('')
  const text = value ?? inner
  const setText = onChange ?? setInner

  function submit(e: FormEvent) {
    e.preventDefault()
    const q = text.trim()
    if (!q || pending) return
    onSubmit(q)
  }

  return (
    <form onSubmit={submit} className="space-y-2">
      <div className="relative">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={placeholder ?? '질문을 입력하세요'}
          aria-label="질문"
          disabled={pending}
          className="w-full rounded-btn border border-line-strong bg-surface py-3 pl-4 pr-12 text-base focus:border-primary focus:outline-none"
        />
        <button type="submit" disabled={!text.trim() || pending} aria-label="물어보기" className="absolute right-1 top-1/2 inline-flex size-9 -translate-y-1/2 items-center justify-center rounded-[8px] bg-primary text-white disabled:bg-primary/30">
          <SendHorizonal className="size-4" />
        </button>
      </div>
      {pending && <ElapsedHint />}
      {!pending && samples && samples.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {samples.map((s) => (
            <button key={s} type="button" onClick={() => setText(s)} className="rounded-full border border-line bg-surface px-3 py-1.5 text-[13px] text-ink-2 hover:bg-canvas">
              {s}
            </button>
          ))}
        </div>
      )}
    </form>
  )
}

function ElapsedHint() {
  const [started] = useState(() => Date.now())
  const [now, setNow] = useState(started)
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 500)
    return () => clearInterval(t)
  }, [])
  const elapsed = Math.floor((now - started) / 1000)
  return (
    <p className="text-sm text-ink-3" role="status">
      답을 준비하는 중 ({elapsed}초). 보통 {QUESTION_WAIT_HINT_SECONDS}초 안팎, 문서는 1분쯤 걸립니다.
    </p>
  )
}
