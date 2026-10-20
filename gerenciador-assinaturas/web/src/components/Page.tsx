import { Inbox, LoaderCircle } from 'lucide-react'
import { useEffect, type ReactNode } from 'react'
import { Card } from './ui/card'

export function PageHeader({ eyebrow = 'Gestão de assinaturas', title, subtitle, actions }: { eyebrow?: string; title: string; subtitle: string; actions?: ReactNode }) {
  useEffect(() => { document.title = `${title} · Licenzy` }, [title])
  return (
    <div className="mb-6 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
      <div className="min-w-0">
        <p className="mb-1 text-xs font-bold uppercase tracking-[0.16em] text-primary">{eyebrow}</p>
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">{title}</h1>
        <p className="mt-1.5 max-w-2xl text-sm text-muted-foreground">{subtitle}</p>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2 max-sm:[&>button]:flex-1">{actions}</div>}
    </div>
  )
}

export function KpiCard({ label, value, hint, icon, danger = false, children }: { label: string; value: ReactNode; hint?: string; icon?: ReactNode; danger?: boolean; children?: ReactNode }) {
  return (
    <Card className="relative min-h-32 overflow-hidden p-5 transition-[transform,border-color,box-shadow] duration-200 hover:-translate-y-0.5 hover:border-primary/20 hover:shadow-[var(--shadow-card-hover)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">{label}</p>
          <p className={`mt-2 text-2xl font-bold tabular-nums ${danger ? 'text-danger' : 'text-foreground'}`}>{value}</p>
          {hint && <p className="mt-1.5 text-xs text-muted-foreground">{hint}</p>}
        </div>
        {icon && <span aria-hidden="true" className="rounded-xl bg-primary/10 p-2.5 text-primary">{icon}</span>}
      </div>
      {children}
    </Card>
  )
}

export function Loading({ label = 'Carregando dados…' }: { label?: string }) {
  return <div role="status" aria-live="polite" className="flex min-h-[45vh] flex-col items-center justify-center gap-3 text-sm text-muted-foreground"><LoaderCircle aria-hidden="true" className="size-7 animate-spin text-primary" /><span>{label}</span></div>
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return <Card className="flex min-h-60 flex-col items-center justify-center p-8 text-center"><span aria-hidden="true" className="rounded-2xl bg-primary/10 p-4 text-primary"><Inbox className="size-7" /></span><h2 className="mt-4 font-semibold">{title}</h2>{description && <p className="mt-1 max-w-md text-sm text-muted-foreground">{description}</p>}{action && <div className="mt-5">{action}</div>}</Card>
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div role="alert" className="mb-5 flex flex-col items-start justify-between gap-3 rounded-xl border border-red-300/60 bg-red-50 px-4 py-3 text-sm text-red-800 sm:flex-row sm:items-center dark:border-red-900 dark:bg-red-950/40 dark:text-red-200"><span>{message} {onRetry && 'Verifique sua conexão e tente novamente.'}</span>{onRetry && <button className="shrink-0 rounded-md font-semibold underline underline-offset-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-current" onClick={onRetry}>Tentar de novo</button>}</div>
}
