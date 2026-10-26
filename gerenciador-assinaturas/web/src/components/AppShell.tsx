import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as DialogPrimitive from '@radix-ui/react-dialog'
import { Link, Outlet, useNavigate, useRouterState } from '@tanstack/react-router'
import { BarChart3, BellRing, ChevronsLeft, ClipboardClock, FileText, FolderKanban, LayoutDashboard, LogOut, Menu, Moon, RefreshCcw, Sun, Users, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { api } from '../lib/api'
import { useSessao } from '../lib/sessao'
import { cn } from '../lib/utils'
import { Badge } from './ui/badge'
import { Button } from './ui/button'

const navegacao = [
  { label: 'Assinaturas', href: '/assinaturas', icon: BarChart3, grupo: 'Visão geral' },
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, grupo: 'Visão geral' },
  { label: 'Pessoas', href: '/pessoas', icon: Users, grupo: 'Gestão' },
  { label: 'Projetos', href: '/projetos', icon: FolderKanban, grupo: 'Gestão' },
  { label: 'Relatórios', href: '/relatorios', icon: FileText, grupo: 'Análise e controle' },
  { label: 'Histórico', href: '/historico', icon: ClipboardClock, grupo: 'Análise e controle' },
  { label: 'Pendências', href: '/pendencias', icon: BellRing, grupo: 'Análise e controle' },
]

function useMenuRecolhido() {
  const [recolhido, setRecolhido] = useState(() => localStorage.getItem('licenzy-menu') === 'recolhido')
  useEffect(() => { localStorage.setItem('licenzy-menu', recolhido ? 'recolhido' : 'expandido') }, [recolhido])
  useEffect(() => {
    const atalho = (event: KeyboardEvent) => {
      const alvo = event.target as HTMLElement
      if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== 'b' || alvo.closest('input, textarea, select, [contenteditable="true"]')) return
      event.preventDefault()
      setRecolhido((atual) => !atual)
    }
    window.addEventListener('keydown', atalho)
    return () => window.removeEventListener('keydown', atalho)
  }, [])
  return [recolhido, setRecolhido] as const
}

function useTheme() {
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem('licenzy-theme')
    return saved ? saved === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches
  })
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('licenzy-theme', dark ? 'dark' : 'light')
    document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]').forEach((meta) => { meta.content = dark ? '#071a2f' : '#f5f7fa' })
  }, [dark])
  return [dark, setDark] as const
}

export function AppShell() {
  const [mobile, setMobile] = useState(false)
  const [dark, setDark] = useTheme()
  const [recolhido, setRecolhido] = useMenuRecolhido()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const pathname = useRouterState({ select: (state) => state.location.pathname })
  const resumo = useQuery({ queryKey: ['sistema'], queryFn: () => api<{ pendencias: number; projetos_pendentes: number; modo_local: boolean }>('/api/sistema/resumo'), refetchInterval: 60_000 })
  const sessao = useSessao()
  const atualizar = useMutation({
    mutationFn: () => api<{ mensagem: string }>('/api/sistema/atualizar', { method: 'POST' }),
    onSuccess: async (data) => { await queryClient.invalidateQueries(); toast.success(data.mensagem) },
    onError: (error: Error) => toast.error(error.message),
  })
  const logout = useMutation({
    mutationFn: () => api('/api/logout', { method: 'POST' }),
    onSettled: () => navigate({ to: '/login' }),
  })

  const pendencias = resumo.data?.pendencias ?? 0
  const itemBase = 'flex h-10 items-center gap-3 rounded-[var(--radius-sm)] text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring'
  const renderSidebar = (compacto: boolean, id?: string) => (
    <aside id={id} aria-label="Navegação principal" className={cn('flex h-full flex-col overflow-hidden whitespace-nowrap border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-200 ease-out', compacto ? 'w-[72px]' : 'w-64')}>
      <div className={cn('flex h-[72px] shrink-0 items-center border-b border-sidebar-border', compacto ? 'justify-center px-0' : 'gap-2 px-3')}>
        {compacto ? (
          <button className="hidden size-10 place-items-center rounded-[var(--radius-sm)] text-sidebar-foreground/70 transition-colors hover:bg-sidebar-hover hover:text-sidebar-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring lg:grid" onClick={() => setRecolhido(false)} aria-label="Expandir menu" aria-controls="menu-lateral" aria-expanded="false" title="Expandir menu (Ctrl+B)"><Menu aria-hidden="true" className="size-5" /></button>
        ) : (
          <>
            <div className="flex min-w-0 flex-1 items-center" role="img" aria-label="Instituto Recôncavo de Tecnologia">
              <span className="flex h-12 w-36 shrink-0 items-center justify-center overflow-hidden">
                <img src={dark ? '/Logo Recôncavo em Branco.png' : '/logo_reconcavo.png'} alt="" width="140" height="40" className="h-full w-full object-contain" />
              </span>
            </div>
            <button className="hidden size-10 shrink-0 place-items-center rounded-[var(--radius-sm)] text-sidebar-foreground/70 transition-colors hover:bg-sidebar-hover hover:text-sidebar-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring lg:grid" onClick={() => setRecolhido(true)} aria-label="Recolher menu" aria-controls="menu-lateral" aria-expanded="true" title="Recolher menu (Ctrl+B)"><ChevronsLeft aria-hidden="true" className="size-5" /></button>
            <button className="ml-auto rounded-lg p-2 hover:bg-sidebar-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring lg:hidden" onClick={() => setMobile(false)} aria-label="Fechar menu"><X aria-hidden="true" className="size-5" /></button>
          </>
        )}
      </div>
      <nav aria-label="Seções" className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-4">
        {[...new Set(navegacao.map((item) => item.grupo))].map((grupo, indice) => (
          <div key={grupo} className="mb-5">
            {compacto
              ? <>{indice > 0 && <span aria-hidden="true" className="mx-auto mb-3 block h-px w-6 bg-sidebar-border" />}<p className="sr-only">{grupo}</p></>
              : <p className="mb-1.5 px-3 text-xs font-medium text-sidebar-muted">{grupo}</p>}
            <div className="space-y-0.5">
              {navegacao.filter((item) => item.grupo === grupo).map(({ label, href, icon: Icon }) => {
                const ativo = pathname === href || pathname.startsWith(`${href}/`)
                const badge = label === 'Pendências' ? pendencias : label === 'Projetos' && sessao.data?.usuario.perfil === 'financeiro' ? (resumo.data?.projetos_pendentes ?? 0) : 0
                const temBadge = badge > 0
                return <Link key={href} to={href} title={compacto ? (temBadge ? `${label} (${badge})` : label) : undefined} aria-current={ativo ? 'page' : undefined} onClick={() => setMobile(false)} className={cn(itemBase, 'relative font-medium', compacto ? 'justify-center px-0' : 'px-3', ativo ? 'bg-primary text-white shadow-[0_6px_20px_-8px_var(--primary)]' : 'text-sidebar-foreground/70 hover:bg-sidebar-hover hover:text-sidebar-foreground')}>
                  <Icon aria-hidden="true" className="size-[18px] shrink-0" />
                  <span className={cn(compacto && 'sr-only')}>{label}</span>
                  {temBadge && (compacto
                    ? <span aria-label={`${badge} itens`} className={cn('absolute right-3 top-2 size-2 rounded-full ring-2', ativo ? 'bg-white ring-primary' : 'bg-urgente ring-sidebar')} />
                    : <span aria-label={`${badge} itens`} className={cn('ml-auto rounded-full px-2 py-0.5 text-[10px] font-bold', ativo ? 'bg-white/20 text-white' : 'bg-urgente/15 text-urgente')}>{badge}</span>)}
                </Link>
              })}
            </div>
          </div>
        ))}
      </nav>
      <div className="space-y-3 p-3">
        {!compacto && sessao.data?.usuario && <div className="whitespace-normal border-b border-sidebar-border px-3 pb-3"><p className="truncate text-sm font-semibold">{sessao.data.usuario.nome}</p><p className="mt-0.5 truncate text-xs text-sidebar-muted">{sessao.data.usuario.email}</p><Badge tone={sessao.data.usuario.perfil === 'financeiro' ? 'green' : 'blue'} className="mt-2">{sessao.data.usuario.perfil === 'financeiro' ? 'Financeiro' : 'Suporte'}</Badge></div>}
        <div className="space-y-0.5">
          <button role="switch" aria-checked={dark} title={compacto ? 'Tema escuro' : undefined} className={cn(itemBase, 'w-full text-sidebar-foreground/70 hover:bg-sidebar-hover hover:text-sidebar-foreground', compacto ? 'justify-center px-0' : 'px-3')} onClick={() => setDark(!dark)}>
            {dark ? <Moon aria-hidden="true" className="size-[18px] shrink-0" /> : <Sun aria-hidden="true" className="size-[18px] shrink-0" />}<span className={cn(compacto && 'sr-only')}>Tema escuro</span>
            {!compacto && <span aria-hidden="true" className={cn('ml-auto flex h-5 w-9 items-center rounded-full p-0.5 transition-colors', dark ? 'bg-primary' : 'bg-muted-strong')}><span className={cn('size-4 rounded-full bg-white shadow transition-transform', dark && 'translate-x-4')} /></span>}
          </button>
          <button title={compacto ? 'Sair' : undefined} className={cn(itemBase, 'w-full text-sidebar-foreground/70 hover:bg-sidebar-hover hover:text-sidebar-foreground disabled:opacity-50', compacto ? 'justify-center px-0' : 'px-3')} onClick={() => logout.mutate()} disabled={logout.isPending}><LogOut aria-hidden="true" className="size-[18px] shrink-0" /><span className={cn(compacto && 'sr-only')}>{logout.isPending ? 'Saindo…' : 'Sair'}</span></button>
        </div>
      </div>
    </aside>
  )

  return (
    <div className="min-h-screen bg-background text-foreground">
      <a href="#conteudo-principal" className="skip-link">Pular para o conteúdo</a>
      <div className="fixed inset-y-0 left-0 z-40 hidden lg:block">{renderSidebar(recolhido, 'menu-lateral')}</div>
      <DialogPrimitive.Root open={mobile} onOpenChange={setMobile}>
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-slate-950/55 data-[state=open]:animate-fade-in lg:hidden" />
          <DialogPrimitive.Content className="fixed inset-y-0 left-0 z-50 overscroll-contain focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-ring lg:hidden">
            <DialogPrimitive.Title className="sr-only">Menu principal</DialogPrimitive.Title>
            {renderSidebar(false)}
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>
      <div className={cn('transition-[padding] duration-200 ease-out', recolhido ? 'lg:pl-[72px]' : 'lg:pl-64')}>
        <header className="sticky top-0 z-30 flex h-[72px] items-center border-b border-border bg-background/90 px-4 backdrop-blur-xl sm:px-6 lg:px-8">
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobile(true)} aria-label="Abrir menu" aria-expanded={mobile}><Menu aria-hidden="true" className="size-5" /></Button>
          <div className="ml-3 hidden min-w-0 sm:block lg:ml-0">
            <p className="truncate text-xs font-medium text-muted-foreground">Gestão de licenças e assinaturas</p>
          </div>
          <div className="ml-auto flex items-center gap-3">
            {resumo.data?.modo_local && <span className="hidden rounded-full bg-atencao/12 px-3 py-1 text-xs font-semibold text-atencao sm:inline">Modo local</span>}
            <Button variant="outline" size="sm" onClick={() => atualizar.mutate()} disabled={atualizar.isPending}><RefreshCcw aria-hidden="true" className={cn('size-3.5', atualizar.isPending && 'animate-spin')} />{atualizar.isPending ? 'Atualizando…' : 'Atualizar'}</Button>
          </div>
        </header>
        <main id="conteudo-principal" tabIndex={-1} className="mx-auto max-w-[1500px] px-4 py-6 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-ring sm:px-6 sm:py-7 lg:px-8"><Outlet /></main>
      </div>
    </div>
  )
}
