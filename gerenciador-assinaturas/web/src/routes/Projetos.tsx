import { useMutation,useQuery,useQueryClient } from '@tanstack/react-query'
import { CheckCircle2,Edit3,Eye,FolderKanban,Plus,RefreshCcw,Search,Send,ShieldCheck,Trash2,UserRound } from 'lucide-react'
import { useEffect,useMemo,useRef,useState } from 'react'
import { toast } from 'sonner'
import { EmptyState,ErrorBanner,KpiCard,Loading,PageHeader } from '../components/Page'
import { Badge,statusTone } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Dialog } from '../components/ui/dialog'
import { Input,Textarea } from '../components/ui/form'
import { ProjetoForm,type ProjetoValores } from '../features/ProjetoForm'
import { RevisaoProjeto } from '../features/RevisaoProjeto'
import { ApiError,api } from '../lib/api'
import { dataHora,normalizar,reais } from '../lib/format'
import { useEhFinanceiro,useSessao } from '../lib/sessao'
import { useUrlState } from '../lib/url-state'
import type { Assinatura,Listas,PessoaProjeto,Projeto } from '../types'

interface Resposta{itens:Projeto[];assinaturas:Assinatura[];pessoas:PessoaProjeto[];listas:Listas;indicadores:{projetos:number;ativos:number;pendentes:number;recusados:number;custo_mensal:number}}
const ABAS=[{valor:'',rotulo:'Todos'},{valor:'Pendente',rotulo:'Pendentes'},{valor:'Recusado',rotulo:'Recusados'},{valor:'Ativo',rotulo:'Ativos'},{valor:'Concluído',rotulo:'Concluídos'}] as const

export function ProjetosPage(){
  const client=useQueryClient()
  const query=useQuery({queryKey:['projetos'],queryFn:()=>api<Resposta>('/api/projetos')})
  const sessao=useSessao()
  const financeiro=useEhFinanceiro()
  const [form,setForm]=useState<Projeto|'novo'|null>(null)
  const [detalhe,setDetalhe]=useState<Projeto|null>(null)
  const [excluir,setExcluir]=useState<Projeto|null>(null)
  const [concluir,setConcluir]=useState<Projeto|null>(null)
  const [revisar,setRevisar]=useState<Projeto|null>(null)
  const [recusar,setRecusar]=useState(false)
  const [motivo,setMotivo]=useState('')
  const [busca,setBusca]=useUrlState('busca','')
  const [aba,setAba]=useUrlState('status','')
  // O Financeiro abre em Pendentes quando há algo para decidir (só na primeira carga, sem filtro na URL)
  const abaInicial=useRef(false)
  useEffect(()=>{
    if(abaInicial.current||!query.data||!sessao.data)return
    abaInicial.current=true
    if(financeiro&&!new URLSearchParams(location.search).has('status')&&query.data.indicadores.pendentes>0)setAba('Pendente')
  },[query.data,sessao.data,financeiro,setAba])
  const refresh=()=>client.invalidateQueries()
  const fecharRevisao=()=>{setRevisar(null);setRecusar(false);setMotivo('');acao.reset()}
  const salvar=useMutation({mutationFn:(v:ProjetoValores)=>{const item=form==='novo'?null:form;const payload={dados:{Nome:v.nome,Cliente:v.cliente,Responsavel:v.responsavel,Departamento:v.departamento,Observacoes:v.observacoes},equipe:v.equipe,original:item};return api<{id:string;status:string}>(item?`/api/projetos/${item.ID}`:'/api/projetos',{method:item?'PUT':'POST',body:JSON.stringify(payload)})},onSuccess:async(r)=>{setForm(null);await refresh();toast.success(r.status==='Pendente'?'Projeto enviado para aprovação do Financeiro.':'Projeto salvo.')}})
  const acao=useMutation({mutationFn:({item,caminho,body}:{item:Projeto;caminho:string;body?:object})=>api(`/api/projetos/${item.ID}/${caminho}`,{method:'POST',body:JSON.stringify(body||{original:item})}),onSuccess:async(_,{caminho})=>{fecharRevisao();setConcluir(null);await refresh();toast.success({ativar:'Projeto ativado. As tecnologias já valem para a equipe.',recusar:'Projeto recusado e devolvido ao Suporte.',concluir:'Projeto concluído.','solicitar-ativacao':'Ativação solicitada ao Financeiro.'}[caminho]||'Projeto atualizado.')},onError:(e:Error)=>{if(!(e instanceof ApiError&&e.status===409&&revisar))toast.error(e.message)}})
  const remover=useMutation({mutationFn:(item:Projeto)=>api(`/api/projetos/${item.ID}`,{method:'DELETE',body:JSON.stringify({original:item})}),onSuccess:async()=>{setExcluir(null);await refresh();toast.success('Projeto excluído.')},onError:(e:Error)=>toast.error(e.message)})
  const filtrado=useMemo(()=>(query.data?.itens||[]).filter((item)=>(!aba||normalizar(item.Status)===normalizar(aba))&&(!busca||normalizar(`${item.Nome} ${item.Cliente} ${item['Responsável']}`).includes(normalizar(busca)))),[query.data,busca,aba])
  if(query.isLoading)return <Loading/>
  if(query.isError)return <><PageHeader title="Projetos" subtitle="Equipe, tecnologias e aprovações"/><ErrorBanner message={(query.error as Error).message} onRetry={()=>query.refetch()}/></>
  const d=query.data!
  const conflitoRevisao=acao.error instanceof ApiError&&acao.error.status===409
  const podeExcluir=(item:Projeto)=>financeiro||(!item['Aprovado em']&&(item.Status==='Pendente'||item.Status==='Recusado'))
  const tituloAba=ABAS.find((a)=>a.valor===aba)?.rotulo.toLocaleLowerCase('pt-BR')||'cadastrado'
  return <>
    <PageHeader title="Projetos" subtitle="Acompanhe equipes, acessos e decisões do Financeiro" actions={<Button variant="primary" onClick={()=>setForm('novo')} disabled={!d.assinaturas.length||!d.pessoas.length}><Plus className="size-4"/>Novo projeto</Button>}/>
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><KpiCard label="Pendentes" value={d.indicadores.pendentes}/><KpiCard label="Ativos" value={d.indicadores.ativos}/><KpiCard label="Recusados" value={d.indicadores.recusados}/><KpiCard label="Custo mensal ativo" value={reais(d.indicadores.custo_mensal)} icon={<FolderKanban className="size-5"/>}/></section>
    <Card className="my-5 p-4"><div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between"><div role="tablist" aria-label="Status do projeto" className="flex flex-wrap gap-1">{ABAS.map(({valor,rotulo})=>{const qtd=valor?d.itens.filter((i)=>i.Status===valor).length:d.itens.length;return <button key={rotulo} type="button" role="tab" aria-selected={aba===valor} onClick={()=>setAba(valor)} className={`rounded-lg px-3 py-2 text-sm font-semibold ${aba===valor?'bg-primary text-white':'text-muted-foreground hover:bg-muted'}`}>{rotulo} <span className="ml-1 opacity-75">{qtd}</span></button>})}</div><div className="relative w-full lg:max-w-sm"><Search className="pointer-events-none absolute left-3 top-3 size-4 text-muted-foreground"/><Input className="pl-9" value={busca} onChange={(e)=>setBusca(e.target.value)} placeholder="Buscar projeto…" aria-label="Buscar projetos"/></div></div></Card>
    {!filtrado.length?<EmptyState title={`Nenhum projeto ${aba?tituloAba:''}`.trim()} description="Os projetos deste status aparecerão aqui."/>:<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{filtrado.map((item)=>{
      const tecnologias=new Set(item.equipe.flatMap((m)=>m.assinaturas.map((a)=>a.id))).size
      return <Card key={item.ID} className="flex flex-col p-5"><div className="flex items-start justify-between"><span className="rounded-xl bg-primary/10 p-2.5 text-primary"><FolderKanban className="size-5"/></span><Badge tone={statusTone(item.Status)}>{item.Status}</Badge></div><h2 className="mt-4 text-lg font-bold">{item.Nome}</h2><p className="mt-1 text-sm text-muted-foreground">{item.Cliente||'Sem cliente'}</p>
        {item.Status==='Recusado'&&item['Motivo da recusa']&&<p className="mt-3 rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-700 dark:text-red-300"><strong>Motivo:</strong> {item['Motivo da recusa']}</p>}
        <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground"><UserRound className="size-3.5"/>{item['Responsável']||'Sem responsável'}</div>
        {item['Aprovado em']&&<p className="mt-1.5 text-xs text-muted-foreground">Aprovado por {item['Aprovado por']||'—'} em {dataHora(item['Aprovado em'])}</p>}
        <div className="mt-5 grid grid-cols-3 gap-3 border-t border-border pt-4"><Metric label="Mensal" value={reais(item['Custo mensal'])}/><Metric label="Pessoas" value={String(item.equipe.length)}/><Metric label="Tecnologias" value={String(tecnologias)}/></div>
        <div className="mt-4 flex flex-wrap justify-end gap-1">
          <Button size="sm" variant="ghost" onClick={()=>setDetalhe(item)}><Eye className="size-3.5"/>Visualizar</Button>
          {item.Status==='Pendente'&&financeiro&&<Button size="sm" variant="primary" onClick={()=>setRevisar(item)}><ShieldCheck className="size-3.5"/>Revisar</Button>}
          {item.Status!=='Concluído'&&<Button size="sm" variant="ghost" onClick={()=>setForm(item)}><Edit3 className="size-3.5"/>Editar</Button>}
          {item.Status==='Recusado'&&<Button size="sm" variant="outline" disabled={acao.isPending} onClick={()=>acao.mutate({item,caminho:'solicitar-ativacao'})}><Send className="size-3.5"/>Solicitar ativação</Button>}
          {item.Status==='Ativo'&&<Button size="sm" variant="ghost" onClick={()=>setConcluir(item)}><CheckCircle2 className="size-3.5"/>Concluir</Button>}
          {podeExcluir(item)&&<Button size="icon" variant="ghost" className="text-danger" onClick={()=>setExcluir(item)} aria-label={`Excluir ${item.Nome}`}><Trash2 className="size-4"/></Button>}
        </div></Card>})}</div>}
    <Dialog open={form!==null} onOpenChange={(o)=>{if(!o){setForm(null);salvar.reset()}}} title={form==='novo'?'Novo projeto':'Editar projeto'} description="Defina as pessoas e as tecnologias que cada uma usará." wide><ProjetoForm item={form==='novo'?null:form} listas={d.listas} assinaturas={d.assinaturas} pessoas={d.pessoas} saving={salvar.isPending} serverError={salvar.error as Error|null} onSubmit={(v)=>salvar.mutate(v)} onCancel={()=>{setForm(null);salvar.reset()}}/></Dialog>
    <Dialog open={!!detalhe} onOpenChange={(o)=>!o&&setDetalhe(null)} title={detalhe?.Nome||'Projeto'} description={detalhe?`${detalhe.Cliente||'Sem cliente'} · ${detalhe.Status}`:undefined} wide>{detalhe&&<RevisaoProjeto projeto={detalhe}/>}</Dialog>
    <Dialog open={!!revisar} onOpenChange={(o)=>{if(!o)fecharRevisao()}} title={revisar?`Revisar ${revisar.Nome}`:'Revisar projeto'} description="Confira equipe, tecnologias e custo antes de decidir." wide>{revisar&&<>
      <RevisaoProjeto projeto={revisar}/>
      {conflitoRevisao?<div role="alert" className="mt-5 flex flex-col gap-3 rounded-xl border border-amber-300/60 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 sm:flex-row sm:items-center sm:justify-between dark:text-amber-100"><span>Alguém alterou a equipe deste projeto enquanto você revisava. Atualize para ver a versão nova antes de decidir.</span><Button size="sm" variant="outline" onClick={async()=>{fecharRevisao();await refresh()}}><RefreshCcw className="size-3.5"/>Atualizar</Button></div>
      :recusar?<div className="mt-5 border-t border-border pt-5"><label className="mb-2 block text-sm font-semibold" htmlFor="motivo-recusa">Motivo da recusa</label><Textarea id="motivo-recusa" value={motivo} onChange={(e)=>setMotivo(e.target.value)} placeholder="Explique o que o Suporte precisa corrigir…" aria-describedby="motivo-ajuda"/><p id="motivo-ajuda" className="mt-1.5 text-xs text-muted-foreground">Obrigatório, com pelo menos 10 caracteres ({motivo.trim().length}/10).</p><div className="mt-4 flex justify-end gap-2"><Button variant="ghost" onClick={()=>setRecusar(false)}>Voltar</Button><Button variant="danger" disabled={motivo.trim().length<10||acao.isPending} onClick={()=>acao.mutate({item:revisar,caminho:'recusar',body:{original:revisar,motivo:motivo.trim()}})}>Confirmar recusa</Button></div></div>
      :<div className="mt-5 flex justify-end gap-2 border-t border-border pt-5"><Button variant="danger" onClick={()=>setRecusar(true)}>Recusar</Button><Button variant="primary" disabled={acao.isPending} onClick={()=>acao.mutate({item:revisar,caminho:'ativar'})}>{acao.isPending?'Ativando…':'Ativar projeto'}</Button></div>}
    </>}</Dialog>
    <Dialog open={!!concluir} onOpenChange={(o)=>!o&&setConcluir(null)} title="Concluir projeto"><p className="text-sm">Concluir <strong>{concluir?.Nome}</strong>?</p><p className="mt-2 text-xs text-muted-foreground">As tecnologias deste projeto saem das pessoas. O histórico é preservado e esta operação não pode ser desfeita.</p><div className="mt-6 flex justify-end gap-2"><Button variant="ghost" onClick={()=>setConcluir(null)}>Cancelar</Button><Button variant="primary" disabled={acao.isPending} onClick={()=>concluir&&acao.mutate({item:concluir,caminho:'concluir'})}>Concluir</Button></div></Dialog>
    <Dialog open={!!excluir} onOpenChange={(o)=>!o&&setExcluir(null)} title="Excluir projeto"><p className="text-sm">Excluir <strong>{excluir?.Nome}</strong> e a equipe dele?</p>{excluir?.['Aprovado em']&&<p className="mt-2 text-xs text-muted-foreground">Este projeto já foi ativado. O caminho normal é Concluir, que preserva o histórico.</p>}<div className="mt-6 flex justify-end gap-2"><Button variant="ghost" onClick={()=>setExcluir(null)}>Cancelar</Button><Button variant="danger" disabled={remover.isPending} onClick={()=>excluir&&remover.mutate(excluir)}>Excluir projeto</Button></div></Dialog>
  </>
}

function Metric({label,value}:{label:string;value:string}){return <div><p className="text-[10px] font-semibold uppercase text-muted-foreground">{label}</p><p className="mt-1 font-bold tabular-nums">{value}</p></div>}
