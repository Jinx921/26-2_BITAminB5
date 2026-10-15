export interface SegmentOption<T extends string> {
  value: T
  label: string
}

export interface SegmentedControlProps<T extends string> {
  options: SegmentOption<T>[]
  value: T | undefined
  onChange: (v: T) => void
  size?: 'sm' | 'md' | 'lg'
  /** 가로로 꽉 채워 균등 분할 */
  fill?: boolean
  'aria-label'?: string
  className?: string
}

const SIZE = { sm: 'min-h-9 px-3 text-sm', md: 'min-h-11 px-4 text-base', lg: 'min-h-12 px-4 text-lg' }

/** 세그먼트 컨트롤. 지역 전환, 예/아니오/모름, 상태 필터에 쓴다 */
export function SegmentedControl<T extends string>({ options, value, onChange, size = 'md', fill, className = '', ...a11y }: SegmentedControlProps<T>) {
  return (
    <div role="radiogroup" aria-label={a11y['aria-label']} className={`rounded-btn border border-line-strong bg-surface p-0.5 ${fill ? 'grid w-full auto-cols-fr grid-flow-col' : 'inline-flex'} ${className}`}>
      {options.map((o) => {
        const on = o.value === value
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => onChange(o.value)}
            className={`whitespace-nowrap rounded-[8px] font-semibold transition-colors ${SIZE[size]} ${on ? 'bg-primary text-white' : 'text-ink-2 hover:bg-canvas'}`}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}
