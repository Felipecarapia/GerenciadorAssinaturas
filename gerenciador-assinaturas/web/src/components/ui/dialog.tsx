import * as DialogPrimitive from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '../../lib/utils'

export function Dialog({ open, onOpenChange, title, description, children, wide = false }: { open: boolean; onOpenChange: (open: boolean) => void; title: string; description?: string; children: ReactNode; wide?: boolean }) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-[2px] data-[state=open]:animate-fade-in" />
        <DialogPrimitive.Content className={cn('fixed left-1/2 top-1/2 z-50 max-h-[calc(100dvh-1rem)] w-[calc(100%-1rem)] -translate-x-1/2 -translate-y-1/2 overscroll-contain overflow-y-auto rounded-2xl border border-border bg-card p-0 shadow-2xl focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring data-[state=open]:animate-dialog-in sm:max-h-[90vh] sm:w-[calc(100%-2rem)]', wide ? 'max-w-3xl' : 'max-w-lg')}>
          <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-border bg-card/95 px-6 py-5 backdrop-blur">
            <div>
              <DialogPrimitive.Title className="text-lg font-semibold text-foreground">{title}</DialogPrimitive.Title>
              {description && <DialogPrimitive.Description className="mt-1 text-sm text-muted-foreground">{description}</DialogPrimitive.Description>}
            </div>
            <DialogPrimitive.Close className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring" aria-label="Fechar diálogo"><X aria-hidden="true" className="size-4" /></DialogPrimitive.Close>
          </div>
          <div className="p-6">{children}</div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  )
}
