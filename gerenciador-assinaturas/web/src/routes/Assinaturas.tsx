import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { ColumnDef } from '../lib/table'
import { Download, Edit3, Ellipsis, History, Plus, Search, Trash2, WalletCards } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { toast } from 'sonner'
import { DataTable } from '../components/DataTable'
import { ErrorBanner, KpiCard, Loading, PageHeader } from '../components/Page'
import { Badge, statusTone } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Dialog } from '../components/ui/dialog'
import { Input, Select } from '../components/ui/form'
import { AssinaturaForm, type AssinaturaValores } from '../features/AssinaturaForm'
import { api, baixar } from '../lib/api'
import { data, dataHora, normalizar, reais } from '../lib/format'
import type { Assinatura, Historico, Indicadores, Listas, Pessoa } from '../types'

interface Resposta { itens: Assinatura[]; indicadores: Indicadores; listas: Listas; pessoas: Pessoa[] }

function RowActions({ item, onEdit, onDelete, onPay, onHistory }: { item: Assinatura; onEdit: () => void; onDelete: () => void; onPay: () => void; onHistory: () => void }) {
  const [open, setOpen] = useState(false)
  const [position, setPosition] = useState({ top: 0, left: 0 })
  const anchorRef = useRef<HTMLDivElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const podePagar = ['mensal', 'anual'].includes(normalizar(item.Plano)) && !!item.venc_data
  const toggleMenu = () => {
    if (open) { setOpen(false); return }
    const rect = anchorRef.current?.getBoundingClientRect()
    if (!rect) return
    const width = 224
    const estimatedHeight = 188
    const gap = 8
    const left = Math.max(12, Math.min(rect.right - width, window.innerWidth - width - 12))
    const top = rect.bottom + gap + estimatedHeight <= window.innerHeight - 12
      ? rect.bottom + gap
      : Math.max(12, rect.top - estimatedHeight - gap)
    setPosition({ top, left })
    setOpen(true)
  }
  useEffect(() => {
    if (!open) return
    const focusTimer = window.requestAnimationFrame(() => menuRef.current?.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus())
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      setOpen(false)
      anchorRef.current?.querySelector<HTMLButtonElement>('button')?.focus()
    }
    const closeOnOutsideClick = (event: PointerEvent) => {
      const target = event.target as Node
      if (!menuRef.current?.contains(target) && !anchorRef.current?.contains(target)) setOpen(false)
    }
    const closeOnViewportChange = () => setOpen(false)
    window.addEventListener('keydown', closeOnEscape)
    document.addEventListener('pointerdown', closeOnOutsideClick)
    window.addEventListener('resize', closeOnViewportChange)
    window.addEventListener('scroll', closeOnViewportChange, true)
    return () => {
      window.cancelAnimationFrame(focusTimer)
      window.removeEventListener('keydown', closeOnEscape)
      document.removeEventListener('pointerdown', closeOnOutsideClick)
      window.removeEventListener('resize', closeOnViewportChange)
      window.removeEventListener('scroll', closeOnViewportChange, true)
    }
  }, [open])
  const handleMenuKeys = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return
    event.preventDefault()
    const items = [...(menuRef.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') || [])]
    if (!items.length) return
    const current = items.indexOf(document.activeElement as HTMLButtonElement)
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : event.key === 'ArrowDown' ? (current + 1) % items.length : (current - 1 + items.length) % items.length
    items[next]?.focus()
  }
  const menu = open ? createPortal(
    <div ref={menuRef} role="menu" aria-label={`Ações de ${item.Nome}`} onKeyDown={handleMenuKeys} className="fixed z-[70] w-56 overscroll-contain rounded-xl border border-border bg-card/98 p-1.5 shadow-[var(--shadow-elevated)] backdrop-blur-xl" style={{ top: position.top, left: position.left }}>
      <button role="menuitem" className="menu-action" onClick={() => {setOpen(false);onEdit()}}><Edit3 aria-hidden="true"/>Editar</button>
      <button role="menuitem" className="menu-action" disabled={!podePagar} onClick={() => {setOpen(false);onPay()}}><WalletCards aria-hidden="true"/>Marcar como pago</button>
      <button role="menuitem" className="menu-action" onClick={() => {setOpen(false);onHistory()}}><History aria-hidden="true"/>Histórico</button>
      <button role="menuitem" className="menu-action text-danger" onClick={() => {setOpen(false);onDelete()}}><Trash2 aria-hidden="true"/>Excluir</button>
    </div>,
    document.body,
  ) : null
  return <div ref={anchorRef} className="relative"><Button size="icon" variant="ghost" onClick={toggleMenu} aria-label={`Ações de ${item.Nome}`} aria-haspopup="menu" aria-expanded={open}><Ellipsis aria-hidden="true" className="size-4" /></Button>{menu}</div>
}

function LogoAssinatura({ src, nome }: { src: string | null; nome: string }) {
  const [fonteComErro, setFonteComErro] = useState<string | null>(null)
  if (!src || fonteComErro === src) return <span className="grid size-7 place-items-center rounded-lg bg-primary/10 text-xs font-bold text-primary">{nome[0]}</span>
  return <img src={src} width="28" height="28" loading="lazy" className="size-7 rounded-lg object-contain" alt="" onError={() => setFonteComErro(src)} />
}

export function AssinaturasPage() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['assinaturas'], queryFn: () => api<Resposta>('/api/assinaturas') })
  const [form, setForm] = useState<Assinatura | 'nova' | null>(null)
  const [excluir, setExcluir] = useState<Assinatura | null>(null)
  const [pagar, setPagar] = useState<Assinatura | null>(null)
  const [historico, setHistorico] = useState<Assinatura | null>(null)
  const [busca, setBusca] = useState(() => new URLSearchParams(location.search).get('busca') || '')
  const [status, setStatus] = useState(() => new URLSearchParams(location.search).get('status') || '')
  const [categoria, setCategoria] = useState(() => new URLSearchParams(location.search).get('categoria') || '')
  const [prazo, setPrazo] = useState(() => new URLSearchParams(location.search).get('prazo') || '')
  useEffect(() => { const p = new URLSearchParams(); if(busca)p.set('busca',busca); if(status)p.set('status',status); if(categoria)p.set('categoria',categoria); if(prazo)p.set('prazo',prazo); history.replaceState(null,'',`${location.pathname}${p.size ? `?${p}` : ''}`) }, [busca,status,categoria,prazo])
  useEffect(() => { const id = new URLSearchParams(location.search).get('editar'); if (!id || !query.data) return; const timer = window.setTimeout(() => setForm(query.data!.itens.find((i) => i.ID === id) || null), 0); return () => window.clearTimeout(timer) }, [query.data])
  const invalidate = async () => { await client.invalidateQueries({ queryKey: ['assinaturas'] }); await client.invalidateQueries({ queryKey: ['dashboard'] }); await client.invalidateQueries({ queryKey: ['sistema'] }) }
  const salvar = useMutation({ mutationFn: (values: AssinaturaValores) => {
    const item = form === 'nova' ? null : form
    const payload = { dados: { Nome: values.nome, 'Logo (URL)': values.logo, Categoria: values.categoria, Plano: values.plano, 'Valor (R$)': values.valor, Vencimento: values.vencimento || null, Status: values.status }, usuarios_ids: values.usuarios, original: item }
    return api(item ? `/api/assinaturas/${item.ID}` : '/api/assinaturas', { method: item ? 'PUT' : 'POST', body: JSON.stringify(payload) })
  }, onSuccess: async () => { setForm(null); await invalidate(); toast.success('Assinatura salva.') } })
  const remover = useMutation({ mutationFn: (item: Assinatura) => api(`/api/assinaturas/${item.ID}`, { method: 'DELETE', body: JSON.stringify({ original: item }) }), onSuccess: async () => { setExcluir(null); await invalidate(); toast.success('Assinatura excluída.') }, onError: (error: Error) => toast.error(error.message) })
  const pagamento = useMutation({ mutationFn: (item: Assinatura) => api<{ vencimento:string }>(`/api/assinaturas/${item.ID}/pagamento`, { method: 'POST', body: JSON.stringify({ original: item }) }), onSuccess: async (r) => { setPagar(null); await invalidate(); toast.success(`Pagamento registrado. Próximo vencimento: ${data(r.vencimento)}.`) }, onError: (error: Error) => toast.error(error.message) })
  const filtrado = useMemo(() => (query.data?.itens || []).filter((item) => {
    if (busca && !normalizar(item.Nome).includes(normalizar(busca))) return false
    if (status && item.Status !== status) return false
    if (categoria && item.Categoria !== categoria) return false
    if (prazo === 'vencidas' && !(item.dias !== null && item.dias < 0)) return false
    if (prazo && prazo !== 'vencidas' && !(item.dias !== null && item.dias <= Number(prazo))) return false
    return true
  }), [query.data,busca,status,categoria,prazo])
  const columns: ColumnDef<Assinatura>[] = [
    { accessorKey: 'Nome', header: 'Assinatura', cell: ({row}) => <div className="flex min-w-44 items-center gap-3"><LogoAssinatura src={row.original['Logo (URL)']} nome={row.original.Nome}/><div><p className="font-semibold">{row.original.Nome}</p><p className="text-xs text-muted-foreground">{row.original.Categoria}</p></div></div> },
    { accessorKey: 'Plano', header: 'Plano' },
    { accessorKey: 'mensal', header: 'Custo mensal', cell: ({getValue}) => <span className="font-semibold tabular-nums">{reais(getValue<number>())}</span> },
    { accessorKey: 'venc_data', header: 'Vencimento', cell: ({row}) => <div><p>{data(row.original.venc_data)}</p>{row.original.nivel !== 'nenhum' && <p className={`text-xs ${row.original.nivel === 'vermelho' ? 'text-red-600' : row.original.nivel === 'amarelo' ? 'text-amber-600' : 'text-emerald-600'}`}>{row.original.texto_alerta}</p>}</div> },
    { accessorKey: 'Status', header: 'Status', cell: ({getValue}) => <Badge tone={statusTone(getValue<string>())}>{getValue<string>()}</Badge> },
    { id: 'usuarios', header: 'Usuários', accessorFn: (row) => row.usuarios_ids.length, cell: ({getValue}) => <span>{getValue<number>()}</span> },
    { id: 'actions', enableSorting: false, header: '', cell: ({row}) => <RowActions item={row.original} onEdit={() => setForm(row.original)} onDelete={() => setExcluir(row.original)} onPay={() => setPagar(row.original)} onHistory={() => setHistorico(row.original)} /> },
  ]
  if (query.isLoading) return <Loading />
  if (query.isError) return <><PageHeader title="Assinaturas" subtitle="Todas as ferramentas contratadas" /><ErrorBanner message={(query.error as Error).message} onRetry={() => query.refetch()} /></>
  const d = query.data!
  return <>
    <PageHeader title="Assinaturas" subtitle="Todas as ferramentas contratadas, com valor, vencimento e quem usa" actions={<><Button variant="outline" onClick={() => baixar('/api/assinaturas/exportar/xlsx','assinaturas.xlsx').catch((e) => toast.error(e.message))}><Download className="size-4"/>Exportar</Button><Button variant="primary" onClick={() => setForm('nova')}><Plus className="size-4"/>Nova assinatura</Button></>} />
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><KpiCard label="Cadastradas" value={d.itens.length}/><KpiCard label="Ativas" value={d.indicadores.total_ativas}/><KpiCard label="Gasto mensal" value={reais(d.indicadores.gasto_mensal)}/><KpiCard label="Vencem em 30 dias" value={d.indicadores.vencendo_30} hint={d.indicadores.vencidas ? `${d.indicadores.vencidas} ${d.indicadores.vencidas === 1 ? 'vencida' : 'vencidas'}` : 'Nenhuma vencida'} danger={d.indicadores.vencidas > 0}/></section>
    <Card className="my-5 grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-[2fr_1fr_1fr_1fr_auto]"><div className="relative"><Search aria-hidden="true" className="pointer-events-none absolute left-3 top-3 size-4 text-muted-foreground"/><Input name="busca" autoComplete="off" aria-label="Buscar por nome" value={busca} onChange={(e)=>setBusca(e.target.value)} className="pl-9" placeholder="Buscar por nome…"/></div><Select name="status" autoComplete="off" aria-label="Filtrar por status" value={status} onChange={(e)=>setStatus(e.target.value)}><option value="">Todos os status</option>{d.listas.Status.map((i)=><option key={i}>{i}</option>)}</Select><Select name="categoria" autoComplete="off" aria-label="Filtrar por categoria" value={categoria} onChange={(e)=>setCategoria(e.target.value)}><option value="">Todas as categorias</option>{d.listas.Categorias.map((i)=><option key={i}>{i}</option>)}</Select><Select name="prazo" autoComplete="off" aria-label="Filtrar por vencimento" value={prazo} onChange={(e)=>setPrazo(e.target.value)}><option value="">Todos os vencimentos</option><option value="vencidas">Vencidas</option><option value="7">Até 7 dias</option><option value="30">Até 30 dias</option><option value="60">Até 60 dias</option><option value="90">Até 90 dias</option></Select>{(busca||status||categoria||prazo)&&<Button variant="ghost" onClick={()=>{setBusca('');setStatus('');setCategoria('');setPrazo('')}}>Limpar</Button>}</Card>
    <p aria-live="polite" className="mb-3 text-xs text-muted-foreground">{filtrado.length} de {d.itens.length} {d.itens.length === 1 ? 'assinatura' : 'assinaturas'}. Abra o menu de ações no fim de cada linha para editar.</p><DataTable data={filtrado} columns={columns} empty="Nenhuma assinatura corresponde aos filtros." label="Assinaturas" />
    <Dialog open={form !== null} onOpenChange={(o)=>!o&&setForm(null)} title={form === 'nova' ? 'Nova assinatura' : 'Editar assinatura'} description="Os dados serão validados e gravados na mesma planilha." wide><AssinaturaForm item={form === 'nova' ? null : form} listas={d.listas} pessoas={d.pessoas} saving={salvar.isPending} serverError={salvar.error as Error|null} onSubmit={(v)=>salvar.mutate(v)} onCancel={()=>setForm(null)}/></Dialog>
    <Dialog open={!!excluir} onOpenChange={(o)=>!o&&setExcluir(null)} title="Excluir assinatura"><p className="text-sm">Tem certeza que deseja excluir <strong>{excluir?.Nome}</strong>?</p>{!!excluir?.usuarios_ids.length&&<p className="mt-3 rounded-lg bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-300">Ela também será removida da lista de {excluir.usuarios_ids.length} {excluir.usuarios_ids.length === 1 ? 'pessoa' : 'pessoas'}.</p>}<div className="mt-6 flex flex-wrap justify-end gap-2"><Button variant="ghost" onClick={()=>setExcluir(null)}>Cancelar</Button><Button variant="danger" onClick={()=>excluir&&remover.mutate(excluir)} disabled={remover.isPending}>{remover.isPending ? 'Excluindo…' : 'Excluir assinatura'}</Button></div></Dialog>
    <Dialog open={!!pagar} onOpenChange={(o)=>!o&&setPagar(null)} title="Marcar como pago"><p className="text-sm">Registrar o pagamento de <strong>{pagar?.Nome}</strong>?</p><div className="mt-4 grid grid-cols-1 gap-3 rounded-xl bg-muted p-4 text-sm sm:grid-cols-2"><div><p className="text-xs text-muted-foreground">Vencimento atual</p><p className="mt-1 font-semibold">{data(pagar?.venc_data)}</p></div><div><p className="text-xs text-muted-foreground">Valor da cobrança</p><p className="mt-1 font-semibold tabular-nums">{reais(pagar?.valor_num)}</p></div></div><p className="mt-4 text-xs text-muted-foreground">O vencimento avança um ciclo e a operação fica registrada no histórico.</p><div className="mt-6 flex flex-wrap justify-end gap-2"><Button variant="ghost" onClick={()=>setPagar(null)}>Cancelar</Button><Button variant="primary" onClick={()=>pagar&&pagamento.mutate(pagar)} disabled={pagamento.isPending}>{pagamento.isPending ? 'Registrando…' : 'Confirmar pagamento'}</Button></div></Dialog>
    <HistoricoDialog item={historico} onClose={()=>setHistorico(null)}/>
  </>
}

function HistoricoDialog({item,onClose}:{item:Assinatura|null;onClose:()=>void}) {
  const query = useQuery({queryKey:['assinatura-historico',item?.ID],queryFn:()=>api<{itens:Historico[]}>(`/api/assinaturas/${item!.ID}/historico`),enabled:!!item})
  return <Dialog open={!!item} onOpenChange={(o)=>!o&&onClose()} title="Linha do tempo" description={item?.Nome}><div className="space-y-0">{query.isLoading&&<Loading label="Carregando histórico…"/>}{query.data?.itens.map((evento,index)=><div key={index} className="relative border-l border-border pb-5 pl-5 last:pb-0"><span className="absolute -left-1 top-1 size-2 rounded-full bg-primary"/><p className="text-xs text-muted-foreground">{dataHora(evento._quando || evento['Data e hora'])} · {evento.Origem}</p><p className="mt-1 text-sm font-semibold">{evento.Evento}</p>{(evento['Valor anterior']||evento['Valor novo'])&&<p className="mt-1 text-xs text-muted-foreground">{evento['Valor anterior']||'(vazio)'} → {evento['Valor novo']||'(vazio)'}</p>}</div>)}{query.data&&!query.data.itens.length&&<p className="py-8 text-center text-sm text-muted-foreground">Nenhum registro para esta assinatura.</p>}</div></Dialog>
}
