export type ButtonVariant = 'fill' | 'outline' | 'text' | 'dark' | 'danger'
export type ButtonSize = 'sm' | 'md' | 'lg'

export const VARIANT: Record<ButtonVariant, string> = {
  fill: 'bg-primary text-white hover:bg-primary-strong active:bg-primary-strong disabled:bg-primary/40',
  outline: 'bg-surface text-ink border border-line-strong hover:bg-canvas active:bg-primary-soft disabled:text-ink-3 disabled:border-line',
  text: 'bg-transparent text-primary hover:bg-primary-soft active:bg-primary-soft disabled:text-ink-3',
  dark: 'bg-navy text-white hover:bg-black active:bg-black disabled:bg-navy/40',
  danger: 'bg-danger text-white hover:bg-red-800 disabled:bg-danger/40',
}
export const SIZE: Record<ButtonSize, string> = {
  sm: 'min-h-11 px-3 text-sm gap-1.5',
  md: 'min-h-11 px-4 text-base gap-2',
  lg: 'min-h-13 px-5 text-lg gap-2',
}

/** 링크(a, Link)를 버튼처럼 보이게 하는 클래스 */
export function buttonClass(variant: ButtonVariant = 'fill', size: ButtonSize = 'md', pill = false): string {
  return `inline-flex select-none items-center justify-center gap-2 font-semibold transition-colors ${pill ? 'rounded-full' : 'rounded-btn'} ${VARIANT[variant]} ${SIZE[size]}`
}
