import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'md' | 'lg' | 'xl'

const VARIANT: Record<Variant, string> = {
  primary: 'bg-blue-700 text-white hover:bg-blue-800 disabled:bg-blue-300',
  secondary: 'bg-white text-slate-900 border border-slate-300 hover:bg-slate-100 disabled:text-slate-400',
  ghost: 'bg-transparent text-blue-700 hover:bg-blue-50 disabled:text-slate-400',
  danger: 'bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300',
}
const SIZE: Record<Size, string> = {
  md: 'px-4 py-2 text-base rounded-lg min-h-11',
  lg: 'px-5 py-3 text-lg rounded-xl min-h-14',
  xl: 'px-6 py-4 text-xl rounded-2xl min-h-16',
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  children: ReactNode
}

export function Button({ variant = 'primary', size = 'md', loading, disabled, className = '', children, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-2 font-semibold transition-colors focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-blue-500 disabled:cursor-not-allowed ${VARIANT[variant]} ${SIZE[size]} ${className}`}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading && <span className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent" aria-hidden />}
      {children}
    </button>
  )
}
