import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Loader2 } from 'lucide-react'
import { SIZE, VARIANT, type ButtonSize, type ButtonVariant } from './buttonClass'

export type { ButtonSize, ButtonVariant } from './buttonClass'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  /** 완전 둥근 알약 모양 */
  pill?: boolean
  loading?: boolean
  icon?: ReactNode
  children?: ReactNode
}

export function Button({ variant = 'fill', size = 'md', pill, loading, disabled, icon, className = '', children, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      className={`inline-flex select-none items-center justify-center font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed ${pill ? 'rounded-full' : 'rounded-btn'} ${VARIANT[variant]} ${SIZE[size]} ${className}`}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  )
}
