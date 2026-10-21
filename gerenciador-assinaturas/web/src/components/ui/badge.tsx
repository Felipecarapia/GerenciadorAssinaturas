/* eslint-disable react-refresh/only-export-components */
import type { ReactNode } from 'react'
import { cn } from '../../lib/utils'

export function Badge({ children, tone = 'neutral', className }: { children: ReactNode; tone?: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'neutral'; className?: string }) {
  const tones = {
    blue: 'bg-blue-500/10 text-blue-700 dark:text-blue-300',
    green: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
    yellow: 'bg-amber-500/12 text-amber-700 dark:text-amber-300',
    red: 'bg-red-500/10 text-red-700 dark:text-red-300',
    purple: 'bg-primary/10 text-primary',
    neutral: 'bg-muted text-muted-foreground',
  }
  return <span className={cn('inline-flex min-h-6 items-center whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold', tones[tone], className)}>{children}</span>
}

export const statusTone = (status: string) => {
  const value = status.toLocaleLowerCase('pt-BR')
  if (value.includes('ativa') || value === 'ativo') return 'green' as const
  if (value.includes('teste') || value.includes('paus') || value.includes('pendent')) return 'yellow' as const
  if (value.includes('recus')) return 'red' as const
  if (value.includes('cancel') || value.includes('conclu')) return 'neutral' as const
  return 'blue' as const
}
