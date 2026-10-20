import { useMutation,useQuery,useQueryClient } from '@tanstack/react-query'
import { ArrowRight,CheckCircle2,Link2Off,ShieldAlert,Table2 } from 'lucide-react'
import { useMemo } from 'react'
import { Link } from '@tanstack/react-router'
import { toast } from 'sonner'
import { EmptyState,ErrorBanner,Loading,PageHeader } from '../components/Page'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { api } from '../lib/api'
import { useUrlState } from '../lib/url-state'
import type { Pendencia } from '../types'

export function PendenciasPage(){
  const client=useQueryClient(),query=useQuery({queryKey:['pendencias'],queryFn:()=>api<{itens:Pendencia[];total:number}>('/api/pendencias')})
  const [tipo,setTipo]=useUrlState('tipo','Todos')
  const limpar=useMutation({mutationFn:(id:string)=>api<{removidas:string[]}>(`/api/pendencias/pessoas/${id}/limpar-escolhas`,{method:'POST',body:'{}'}),onSuccess:async d=>{await client.invalidateQueries();toast.success(d.removidas.length?`Removido: ${d.removidas.join(', ')}`:'Nenhuma escolha removida.')},onError:(e:Error)=>toast.error(e.message)})
  const tipos=useMemo(()=>['Todos',...new Set(query.data?.itens.map(i=>i.Tipo)||[])],[query.data]),itens=(query.data?.itens||[]).filter(i=>tipo==='Todos'||i.Tipo===tipo)
  if(query.isLoading)return <Loading/>
  if(query.isError)return <><PageHeader title="Pendências" subtitle="Problemas nos dados da planilha"/><ErrorBanner message={(query.error as Error).message} onRetry={()=>query.refetch()}/></>
  return <><PageHeader title="Pendências" subtitle="Problemas nos dados da planilha que precisam de correção"/>
    {!query.data?.total?<EmptyState title="Nenhuma pendência" description="Os dados da planilha estão consistentes." action={<span className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-600"><CheckCircle2 className="size-4"/>Tudo certo</span>}/>:<>
      <Card className="mb-5 flex items-start gap-3 border-amber-300/60 bg-amber-50 p-4 text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200"><ShieldAlert aria-hidden="true" className="mt-0.5 size-5 shrink-0"/><div><p className="text-sm font-semibold">{query.data.total} {query.data.total === 1 ? 'pendência encontrada' : 'pendências encontradas'}</p><p className="mt-1 text-xs opacity-80">Corrija pelo app ou direto na planilha. Depois, clique em Atualizar.</p></div></Card>
      <div role="group" aria-label="Filtrar por tipo" className="mb-5 flex gap-1 overflow-x-auto rounded-xl bg-muted p-1.5">{tipos.map(i=><button key={i} aria-pressed={tipo===i} onClick={()=>setTipo(i)} className={`shrink-0 rounded-lg px-3 py-2 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${tipo===i?'bg-card text-foreground shadow-sm':'text-muted-foreground hover:text-foreground'}`}>{i}</button>)}</div>
      <div className="space-y-3" aria-live="polite">{itens.map((item,index)=><Card key={`${item.Aba}-${item.Linha}-${index}`} className="flex min-w-0 flex-col justify-between gap-4 p-4 sm:flex-row sm:items-center"><div className="flex min-w-0 gap-3"><span aria-hidden="true" className="h-fit shrink-0 rounded-xl bg-amber-500/10 p-2.5 text-amber-600"><Table2 className="size-5"/></span><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><p className="break-words text-sm font-semibold">{item.Tipo}</p><Badge>{item.Aba} · linha {item.Linha}</Badge></div><p className="mt-1 break-words text-sm text-muted-foreground">{item.Item}</p><p className="mt-1 break-words text-xs text-muted-foreground">{item['Descrição']||item.Descricao}</p></div></div><div className="flex shrink-0 flex-wrap gap-2">{item.Tipo==='Assinatura escolhida não existe'&&<Button size="sm" variant="outline" disabled={limpar.isPending} onClick={()=>limpar.mutate(item.ID)}><Link2Off aria-hidden="true" className="size-3.5"/>{limpar.isPending ? 'Removendo…' : 'Remover inválidas'}</Button>}<Link className="inline-flex h-8 items-center justify-center gap-2 rounded-[var(--radius-sm)] bg-primary px-3 text-xs font-semibold text-white transition-colors hover:bg-primary-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring" to={item.Aba==='Assinaturas'?'/assinaturas':'/pessoas'} search={{editar:item.ID} as never}>Corrigir no app<ArrowRight aria-hidden="true" className="size-3.5"/></Link></div></Card>)}{!itens.length&&<EmptyState title="Nenhuma pendência deste tipo" description="Escolha outro filtro para ver as demais pendências."/>}</div>
    </>}
  </>
}
