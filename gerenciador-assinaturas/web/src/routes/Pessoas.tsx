import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { ColumnDef } from '../lib/table'
import { Download, Edit3, Eye, Plus, Search, Trash2, Users } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { DataTable } from '../components/DataTable'
import { EmptyState, ErrorBanner, KpiCard, Loading, PageHeader } from '../components/Page'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Dialog } from '../components/ui/dialog'
import { Input, Select } from '../components/ui/form'
import { PessoaForm, type PessoaValores } from '../features/PessoaForm'
import { api, baixar } from '../lib/api'
import { iniciais, normalizar, reais } from '../lib/format'
import { useUrlState } from '../lib/url-state'
import type { Assinatura, Listas, Pessoa } from '../types'

interface Resposta { itens: Pessoa[]; listas: Listas; assinaturas: Assinatura[]; indicadores: { colaboradores:number; departamentos:number; custo_medio:number } }
interface Detalhe { item:Pessoa; detalhe:Array<{Assinatura:string;Plano:string;Status:string;Usuários:number;'Custo mensal total':number;'Parte da pessoa':number}>; assinaturas:string[] }

export function PessoasPage() {
  const client=useQueryClient()
  const query=useQuery({queryKey:['pessoas'],queryFn:()=>api<Resposta>('/api/pessoas')})
  const [form,setForm]=useState<Pessoa|'nova'|null>(null),[excluir,setExcluir]=useState<Pessoa|null>(null),[detalhe,setDetalhe]=useState<Pessoa|null>(null)
  const [busca,setBusca]=useUrlState('busca',''),[departamento,setDepartamento]=useUrlState('departamento','')
  useEffect(()=>{const id=new URLSearchParams(location.search).get('editar');if(!id||!query.data)return;const timer=window.setTimeout(()=>setForm(query.data!.itens.find((i)=>i.ID===id)||null),0);return()=>window.clearTimeout(timer)},[query.data])
  const salvar=useMutation({mutationFn:(values:PessoaValores)=>{const item=form==='nova'?null:form;const payload={dados:{'Nome completo':values.nome,'E-mail':values.email,Departamento:values.departamento,Cargo:values.cargo},assinaturas:values.assinaturas,original:item};return api(item?`/api/pessoas/${item.ID}`:'/api/pessoas',{method:item?'PUT':'POST',body:JSON.stringify(payload)})},onSuccess:async()=>{setForm(null);await client.invalidateQueries({queryKey:['pessoas']});await client.invalidateQueries({queryKey:['assinaturas']});toast.success('Pessoa salva.')}})
  const remover=useMutation({mutationFn:(item:Pessoa)=>api(`/api/pessoas/${item.ID}`,{method:'DELETE'}),onSuccess:async()=>{setExcluir(null);await client.invalidateQueries();toast.success('Pessoa excluída.')},onError:(e:Error)=>toast.error(e.message)})
  const filtrado=useMemo(()=>(query.data?.itens||[]).filter((item)=>{const texto=normalizar(`${item['Nome completo']} ${item['E-mail']} ${item.Departamento}`);return(!busca||texto.includes(normalizar(busca)))&&(!departamento||item.Departamento===departamento)}),[query.data,busca,departamento])
  const columns:ColumnDef<Pessoa>[]=[
    {accessorKey:'Nome completo',header:'Pessoa',cell:({row})=><div className="flex min-w-48 items-center gap-3"><span className="grid size-8 shrink-0 place-items-center rounded-full bg-primary/10 text-xs font-bold text-primary">{iniciais(row.original['Nome completo'])}</span><div><p className="font-semibold">{row.original['Nome completo']}</p><p className="text-xs text-muted-foreground">{row.original['E-mail']}</p></div></div>},
    {accessorKey:'Departamento',header:'Departamento'},
    {accessorKey:'Cargo',header:'Cargo',cell:({getValue})=><span className="text-muted-foreground">{getValue<string>()||'—'}</span>},
    {id:'assinaturas',header:'Assinaturas',accessorFn:(row)=>row.assinaturas_lista.length,cell:({row})=><div className="flex max-w-64 flex-wrap gap-1">{row.original.assinaturas_lista.slice(0,2).map((item)=><Badge key={item}>{item}</Badge>)}{row.original.assinaturas_lista.length>2&&<Badge>+{row.original.assinaturas_lista.length-2}</Badge>}{!row.original.assinaturas_lista.length&&<span className="text-muted-foreground">Nenhuma</span>}</div>},
    {accessorKey:'Custo mensal',header:'Custo mensal',cell:({getValue})=><span className="font-semibold">{reais(getValue<number>())}</span>},
    {id:'actions',enableSorting:false,header:'',cell:({row})=><div className="flex justify-end"><Button variant="ghost" size="icon" onClick={()=>setDetalhe(row.original)} aria-label="Ver detalhes"><Eye className="size-4"/></Button><Button variant="ghost" size="icon" onClick={()=>setForm(row.original)} aria-label="Editar"><Edit3 className="size-4"/></Button><Button variant="ghost" size="icon" className="text-danger" onClick={()=>setExcluir(row.original)} aria-label="Excluir"><Trash2 className="size-4"/></Button></div>}
  ]
  if(query.isLoading)return <Loading/>
  if(query.isError)return <><PageHeader title="Pessoas" subtitle="Colaboradores e as assinaturas que cada um usa"/><ErrorBanner message={(query.error as Error).message} onRetry={()=>query.refetch()}/></>
  const d=query.data!
  return <>
    <PageHeader title="Pessoas" subtitle="Colaboradores e as assinaturas que cada um usa" actions={<><Button variant="outline" onClick={()=>baixar('/api/pessoas/exportar/xlsx','pessoas.xlsx').catch(e=>toast.error(e.message))}><Download className="size-4"/>Exportar</Button><Button variant="primary" onClick={()=>setForm('nova')}><Plus className="size-4"/>Nova pessoa</Button></>}/>
    <section className="grid gap-4 sm:grid-cols-3"><KpiCard label="Colaboradores" value={d.indicadores.colaboradores} icon={<Users className="size-5"/>}/><KpiCard label="Departamentos" value={d.indicadores.departamentos}/><KpiCard label="Custo mensal médio" value={reais(d.indicadores.custo_medio)}/></section>
    <Card className="my-5 grid gap-3 p-4 sm:grid-cols-[2fr_1fr]"><div className="relative"><Search aria-hidden="true" className="pointer-events-none absolute left-3 top-3 size-4 text-muted-foreground"/><Input name="busca" autoComplete="off" aria-label="Buscar pessoas" className="pl-9" value={busca} onChange={e=>setBusca(e.target.value)} placeholder="Buscar por nome, e-mail ou departamento…"/></div><Select name="departamento" autoComplete="off" aria-label="Filtrar por departamento" value={departamento} onChange={e=>setDepartamento(e.target.value)}><option value="">Todos os departamentos</option>{d.listas.Departamentos.map(i=><option key={i}>{i}</option>)}</Select></Card>
    {!d.itens.length?<EmptyState title="Nenhuma pessoa cadastrada" description="Cadastre as pessoas antes de vinculá-las às assinaturas." action={<Button variant="primary" onClick={()=>setForm('nova')}><Plus className="size-4"/>Nova pessoa</Button>}/>:<><p aria-live="polite" className="mb-3 text-xs text-muted-foreground">{filtrado.length} de {d.itens.length} {d.itens.length === 1 ? 'pessoa' : 'pessoas'}.</p><DataTable data={filtrado} columns={columns} label="Pessoas"/></>}
    <Dialog open={form!==null} onOpenChange={o=>!o&&setForm(null)} title={form==='nova'?'Nova pessoa':'Editar pessoa'} description="Dados do colaborador e ferramentas que utiliza." wide><PessoaForm item={form==='nova'?null:form} listas={d.listas} assinaturas={d.assinaturas} saving={salvar.isPending} serverError={salvar.error as Error|null} onSubmit={v=>salvar.mutate(v)} onCancel={()=>setForm(null)}/></Dialog>
    <Dialog open={!!excluir} onOpenChange={o=>!o&&setExcluir(null)} title="Excluir pessoa"><p className="text-sm">Tem certeza que deseja excluir <strong>{excluir?.['Nome completo']}</strong>?</p><p className="mt-2 text-xs text-muted-foreground">Os desvínculos ficam registrados no Histórico.</p><div className="mt-6 flex justify-end gap-2"><Button variant="ghost" onClick={()=>setExcluir(null)}>Cancelar</Button><Button variant="danger" disabled={remover.isPending} onClick={()=>excluir&&remover.mutate(excluir)}>Excluir</Button></div></Dialog>
    <PessoaDetalhe item={detalhe} onClose={()=>setDetalhe(null)}/>
  </>
}

function PessoaDetalhe({item,onClose}:{item:Pessoa|null;onClose:()=>void}){
  const query=useQuery({queryKey:['pessoa',item?.ID],queryFn:()=>api<Detalhe>(`/api/pessoas/${item!.ID}`),enabled:!!item})
  const total=query.data?.detalhe.reduce((s,i)=>s+Number(i['Parte da pessoa']||0),0)||0
  return <Dialog open={!!item} onOpenChange={o=>!o&&onClose()} title={item?.['Nome completo']||'Detalhe da pessoa'} description={item?`${item['E-mail']} · ${item.Departamento}`:undefined} wide>{query.isLoading?<Loading/>:<><div className="mb-5 grid grid-cols-2 gap-3"><Card className="p-4"><p className="text-xs text-muted-foreground">Custo mensal que representa</p><p className="mt-1 text-xl font-bold">{reais(total)}</p></Card><Card className="p-4"><p className="text-xs text-muted-foreground">Assinaturas</p><p className="mt-1 text-xl font-bold">{query.data?.detalhe.length||0}</p></Card></div><div className="space-y-2">{query.data?.detalhe.map(i=><div key={i.Assinatura} className="flex items-center justify-between rounded-xl border border-border p-3"><div><p className="text-sm font-semibold">{i.Assinatura}</p><p className="text-xs text-muted-foreground">{i.Plano} · {i.Status}</p></div><div className="text-right"><p className="text-sm font-semibold">{reais(i['Parte da pessoa'])}</p><p className="text-xs text-muted-foreground">de {reais(i['Custo mensal total'])}</p></div></div>)}{query.data&&!query.data.detalhe.length&&<p className="py-8 text-center text-sm text-muted-foreground">Esta pessoa não usa nenhuma assinatura.</p>}</div></>}</Dialog>
}
