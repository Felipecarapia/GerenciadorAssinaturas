import { cloneElement, isValidElement, useId, type InputHTMLAttributes, type ReactElement, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'
import { cn } from '../../lib/utils'

export function Label({ children, required, htmlFor, id }: { children: React.ReactNode; required?: boolean; htmlFor?: string; id?: string }) {
  return <label id={id} htmlFor={htmlFor} className="mb-1.5 block text-sm font-medium text-foreground">{children}{required && <span className="text-danger" aria-hidden="true"> *</span>}{required && <span className="sr-only"> (obrigatório)</span>}</label>
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn('h-10 w-full rounded-[var(--radius-sm)] border border-input bg-background px-3 text-sm transition-[border-color,box-shadow,background-color] placeholder:text-muted-foreground/65 hover:border-muted-foreground/60 focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-danger aria-invalid:ring-danger/20', className)} {...props} />
}

export function Select({ className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn('h-10 w-full rounded-[var(--radius-sm)] border border-input bg-background px-3 text-sm text-foreground transition-[border-color,box-shadow,background-color] hover:border-muted-foreground/60 focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-danger aria-invalid:ring-danger/20', className)} {...props}>{children}</select>
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn('min-h-24 w-full resize-y rounded-[var(--radius-sm)] border border-input bg-background px-3 py-2 text-sm transition-[border-color,box-shadow,background-color] placeholder:text-muted-foreground/65 hover:border-muted-foreground/60 focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-danger aria-invalid:ring-danger/20', className)} {...props} />
}

export function Field({ label, error, required, children, className }: { label: string; error?: string; required?: boolean; children: React.ReactNode; className?: string }) {
  const id = useId()
  const control = isValidElement(children) ? cloneElement(children as ReactElement<{ id?: string; 'aria-describedby'?: string; 'aria-invalid'?: boolean; 'aria-labelledby'?: string; 'aria-required'?: boolean }>, { id, 'aria-describedby': error ? `${id}-error` : undefined, 'aria-invalid': !!error, 'aria-labelledby': `${id}-label`, 'aria-required': required }) : children
  return <div className={className}><Label id={`${id}-label`} required={required} htmlFor={id}>{label}</Label>{control}{error && <p id={`${id}-error`} role="alert" className="mt-1 text-xs font-medium text-danger">{error}</p>}</div>
}

export function MultiCheck({ options, selected, onChange, labels, id, 'aria-describedby': describedBy, 'aria-labelledby': labelledBy, 'aria-invalid': invalid }: { options: string[]; selected: string[]; onChange: (value: string[]) => void; labels?: Record<string, string>; id?: string; 'aria-describedby'?: string; 'aria-labelledby'?: string; 'aria-invalid'?: boolean }) {
  return (
    <div id={id} role="group" aria-describedby={describedBy} aria-labelledby={labelledBy} aria-invalid={invalid} className="max-h-44 space-y-1 overscroll-contain overflow-y-auto rounded-[var(--radius-sm)] border border-input bg-background p-2 aria-invalid:border-danger">
      {options.length === 0 && <p className="px-2 py-3 text-sm text-muted-foreground">Nenhuma opção disponível.</p>}
      {options.map((option) => (
        <label key={option} className="flex cursor-pointer items-center gap-3 rounded-lg px-2 py-2 text-sm hover:bg-muted">
          <input
            type="checkbox"
            checked={selected.includes(option)}
            onChange={(event) => onChange(event.target.checked ? [...selected, option] : selected.filter((item) => item !== option))}
            className="size-4 shrink-0 accent-[var(--primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
          />
          <span>{labels?.[option] || option}</span>
        </label>
      ))}
    </div>
  )
}
