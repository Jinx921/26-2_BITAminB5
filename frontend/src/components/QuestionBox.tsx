import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Button } from '@/components/ui/Button'
import { QUESTION_WAIT_HINT_SECONDS } from '@/config'

export interface QuestionBoxProps {
  onSubmit: (question: string) => void
  pending: boolean
  placeholder?: string
  samples?: string[]
  size?: 'md' | 'lg'
  /** 입력창 왼쪽·오른쪽에 붙일 추가 버튼 (음성 입력 등) */
  extra?: ReactNode
  value?: string
  onChange?: (v: string) => void
}

/** 질문 입력창 + 진행 표시. 답이 15~35초 걸리므로 경과 시간을 보여준다 */
export function QuestionBox({ onSubmit, pending, placeholder, samples, size = 'md', extra, value, onChange }: QuestionBoxProps) {
  const [inner, setInner] = useState('')
  const text = value ?? inner
  const setText = onChange ?? setInner

  function submit(e: FormEvent) {
    e.preventDefault()
    const q = text.trim()
    if (!q || pending) return
    onSubmit(q)
  }

  const big = size === 'lg'
  return (
    <form onSubmit={submit} className="space-y-2">
      <div className="flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={placeholder ?? '질문을 입력하세요'}
          aria-label="질문"
          className={`min-w-0 flex-1 rounded-xl border border-slate-300 bg-white px-4 ${big ? 'py-4 text-xl' : 'py-3 text-base'}`}
          disabled={pending}
        />
        {extra}
        <Button type="submit" size={big ? 'xl' : 'md'} loading={pending} disabled={!text.trim()}>
          {pending ? '답변 중' : '물어보기'}
        </Button>
      </div>
      {pending && <ElapsedHint />}
      {!pending && samples && samples.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {samples.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setText(s)}
              className={`rounded-full border border-slate-300 bg-white px-3 py-1 text-slate-700 hover:bg-slate-100 ${big ? 'text-base' : 'text-sm'}`}
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </form>
  )
}

/** 대기 중 경과 시간. pending 일 때만 마운트되므로 시작 시각은 초기 상태로 잡는다 */
function ElapsedHint() {
  const [started] = useState(() => Date.now())
  const [now, setNow] = useState(started)
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 500)
    return () => clearInterval(t)
  }, [])
  const elapsed = Math.floor((now - started) / 1000)
  return (
    <p className="text-sm text-slate-600" role="status">
      답을 준비하고 있어요 ({elapsed}초). 보통 {QUESTION_WAIT_HINT_SECONDS}초 안팎, 문서는 1분쯤 걸려요.
    </p>
  )
}
