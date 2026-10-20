import type { ButtonHTMLAttributes } from 'react'
import { cn } from '../../lib/utils'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: 'sm' | 'md' | 'icon'
}

export function Button({ className, variant = 'secondary', size = 'md', type = 'button', ...props }: ButtonProps) {
  const variants: Record<Variant, string> = {
    primary: 'bg-primary text-white shadow-sm hover:bg-primary-strong',
    secondary: 'bg-muted text-foreground hover:bg-muted-strong',
    ghost: 'bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground',
    danger: 'bg-danger text-white hover:bg-danger/90',
    outline: 'border border-border bg-card text-foreground hover:bg-muted',
  }
  const sizes = { sm: 'h-8 px-3 text-xs', md: 'h-10 px-4 text-sm', icon: 'size-9 p-0' }
  return (
    <button
      type={type}
      className={cn('inline-flex items-center justify-center gap-2 rounded-[var(--radius-sm)] font-semibold transition-[color,background-color,border-color,box-shadow,transform] duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:pointer-events-none disabled:opacity-45 active:translate-y-px', variants[variant], sizes[size], className)}
      {...props}
    />
  )
}
