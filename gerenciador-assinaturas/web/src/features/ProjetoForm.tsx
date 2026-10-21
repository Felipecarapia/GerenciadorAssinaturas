import { zodResolver } from '@hookform/resolvers/zod'
import { Plus, Trash2 } from 'lucide-react'
import { useEffect, useMemo } from 'react'
import { useFieldArray, useForm, useWatch } from 'react-hook-form'
import { z } from 'zod'
import { ApiError } from '../lib/api'
import { normalizar } from '../lib/format'
import type { Assinatura, Listas, PessoaProjeto, Projeto } from '../types'
import { Button } from '../components/ui/button'
import { Field, Input, MultiCheck, Select, Textarea } from '../components/ui/form'

const schema = z.object({
  nome: z.string().trim().min(1, 'Informe o nome do projeto.'),
  cliente: z.string(),
  responsavel: z.string(),
  departamento: z.string(),
  observacoes: z.string(),
  equipe: z.array(z.object({
    pessoa_id: z.string().min(1, 'Escolha a pessoa.'),
    assinaturas_ids: z.array(z.string()).min(1, 'Escolha pelo menos uma tecnologia.'),
  })).min(1, 'Adicione pelo menos uma pessoa.')
    .refine((lista) => new Set(lista.map((m) => m.pessoa_id)).size === lista.length, 'Essa pessoa já está na equipe.'),
})
export type ProjetoValores = z.infer<typeof schema>

interface Props { item?: Projeto|null; listas:Listas; assinaturas:Assinatura[]; pessoas:PessoaProjeto[]; saving:boolean; serverError?:Error|null; onSubmit:(v:ProjetoValores)=>void; onCancel:()=>void }

const ehRemocao = (situacao: string) => normalizar(situacao) === 'remocao proposta'

function equipeDo(item?:Projeto|null) {
  if (!item) return []
  return item.equipe.map((membro) => ({
    pessoa_id: membro.pessoa_id,
    assinaturas_ids: membro.assinaturas.filter((a) => !ehRemocao(a.situacao) && normalizar(a.situacao) !== 'encerrado').map((a) => a.id),
  })).filter((membro) => membro.assinaturas_ids.length)
}

export function ProjetoForm({item,listas,assinaturas,pessoas,saving,serverError,onSubmit,onCancel}:Props) {
  const form=useForm<ProjetoValores>({resolver:zodResolver(schema),defaultValues:{nome:'',cliente:'',responsavel:'',departamento:'',observacoes:'',equipe:[]}})
  const campos=useFieldArray({control:form.control,name:'equipe'})
  useEffect(()=>{form.reset({nome:item?.Nome||'',cliente:item?.Cliente||'',responsavel:item?.['Responsável']||'',departamento:item?.Departamento||'',observacoes:item?.['Observações']||'',equipe:equipeDo(item)})},[item,form])
  const equipe=useWatch({control:form.control,name:'equipe'})||[]
  useEffect(()=>{
    if(!(serverError instanceof ApiError))return
    Object.entries(serverError.fieldErrors).forEach(([campo,mensagem])=>{
      if(campo==='Nome')form.setError('nome',{message:mensagem})
      else if(campo.startsWith('Equipe.')){const indice=form.getValues('equipe').findIndex((m)=>m.pessoa_id===campo.slice(7));form.setError(indice>=0?`equipe.${indice}.assinaturas_ids`:'equipe',{message:mensagem})}
      else if(campo==='Equipe'||campo==='equipe')form.setError('equipe',{message:mensagem})
    })
  },[serverError,form])
  // Situação atual de cada tecnologia por pessoa, para marcar o que aguarda aprovação ou vai sair
  const situacoes=useMemo(()=>new Map((item?.equipe||[]).map((m)=>[m.pessoa_id,new Map(m.assinaturas.map((a)=>[a.id,a]))])),[item])
  const disponiveis=assinaturas.filter((a)=>['ativa','em teste'].includes(normalizar(a.Status)))
  const nomes=Object.fromEntries(assinaturas.map((a)=>[a.ID,a.Nome]))
  const saemSemLinha=(item?.equipe||[]).filter((m)=>!equipe.some((e)=>e.pessoa_id===m.pessoa_id)&&m.assinaturas.some((a)=>ehRemocao(a.situacao)))
  const erroEquipe=form.formState.errors.equipe
  const mensagemEquipe=typeof erroEquipe?.message==='string'?erroEquipe.message:erroEquipe?.root?.message
  return <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
    {serverError&&!(serverError instanceof ApiError&&Object.keys(serverError.fieldErrors).length)&&<div role="alert" className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-danger">{serverError.message}</div>}
    {item?.Status==='Recusado'&&item['Motivo da recusa']&&<div role="note" className="rounded-xl border border-red-300/60 bg-red-500/10 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:text-red-200"><p className="font-semibold">Recusado pelo Financeiro{item['Recusado por']?` (${item['Recusado por']})`:''}</p><p className="mt-1">{item['Motivo da recusa']}</p></div>}
    {item?.Status==='Ativo'&&<p className="rounded-xl bg-amber-500/10 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">Mudanças na equipe ou nas tecnologias voltam o projeto para aprovação do Financeiro. O que já está aprovado continua valendo.</p>}
    <div className="grid gap-4 sm:grid-cols-2"><Field label="Nome do projeto" required error={form.formState.errors.nome?.message}><Input {...form.register('nome')}/></Field><Field label="Cliente"><Input {...form.register('cliente')}/></Field></div>
    <div className="grid gap-4 sm:grid-cols-2"><Field label="Responsável"><Input {...form.register('responsavel')}/></Field><Field label="Departamento"><Select {...form.register('departamento')}><option value="">Escolha</option>{listas.Departamentos.map((nome)=><option key={nome}>{nome}</option>)}</Select></Field></div>
    <Field label="Observações"><Textarea {...form.register('observacoes')}/></Field>
    <section className="rounded-xl border border-border p-4" aria-labelledby="titulo-equipe"><div className="flex items-start justify-between gap-3"><div><h3 id="titulo-equipe" className="text-sm font-semibold">Equipe</h3><p className="mt-1 text-xs text-muted-foreground">Cada pessoa recebe as tecnologias escolhidas depois que o Financeiro ativar o projeto.</p></div></div>
      <div className="mt-4 space-y-3">{campos.fields.map((campo,index)=>{
        const selecionada=equipe[index]?.pessoa_id||''
        const outras=new Set(equipe.filter((_,i)=>i!==index).map((m)=>m.pessoa_id))
        const daPessoa=situacoes.get(selecionada)
        const marcadas=equipe[index]?.assinaturas_ids||[]
        const opcoes=[...new Set([...disponiveis.map((a)=>a.ID),...marcadas])]
        const labels=Object.fromEntries(opcoes.map((id)=>[id,`${nomes[id]||id}${daPessoa?.get(id)?.situacao==='Proposto'&&marcadas.includes(id)?' · aguardando aprovação':''}`]))
        const saem=[...(daPessoa?.values()||[])].filter((a)=>ehRemocao(a.situacao)&&!marcadas.includes(a.id))
        return <div key={campo.id} className="rounded-xl bg-muted/45 p-4"><div className="flex items-end gap-2"><Field className="flex-1" label="Pessoa" required error={form.formState.errors.equipe?.[index]?.pessoa_id?.message}><Select {...form.register(`equipe.${index}.pessoa_id`)}><option value="">Escolha</option>{pessoas.filter((p)=>!outras.has(p.ID)).map((p)=><option key={p.ID} value={p.ID}>{p['Nome completo']}</option>)}</Select></Field><Button size="icon" variant="ghost" className="text-danger" onClick={()=>campos.remove(index)} aria-label="Remover pessoa"><Trash2 className="size-4"/></Button></div>
          <Field className="mt-3" label="Tecnologias" required error={form.formState.errors.equipe?.[index]?.assinaturas_ids?.message}><MultiCheck options={opcoes} labels={labels} selected={marcadas} onChange={(ids)=>form.setValue(`equipe.${index}.assinaturas_ids`,ids,{shouldValidate:true})}/></Field>
          {!!saem.length&&<ul className="mt-2 space-y-0.5 text-xs text-muted-foreground">{saem.map((a)=><li key={a.id}><span className="line-through">{a.nome}</span> · sai após aprovação</li>)}</ul>}
        </div>})}
        {!campos.fields.length&&<p className="rounded-lg border border-dashed border-border py-8 text-center text-sm text-muted-foreground">Adicione ao menos uma pessoa à equipe.</p>}
        {saemSemLinha.map((m)=><p key={m.pessoa_id} className="rounded-lg border border-dashed border-border px-4 py-3 text-xs text-muted-foreground"><span className="font-semibold line-through">{m.nome}</span> · {m.assinaturas.filter((a)=>ehRemocao(a.situacao)).map((a)=>a.nome).join(', ')} · sai após aprovação</p>)}
      </div>
      {mensagemEquipe&&<p className="mt-2 text-xs font-medium text-danger" role="alert">{mensagemEquipe}</p>}
      <Button size="sm" variant="outline" className="mt-3" onClick={()=>campos.append({pessoa_id:'',assinaturas_ids:[]})} disabled={campos.fields.length>=pessoas.length}><Plus className="size-4"/>Adicionar pessoa</Button>
    </section>
    <div className="flex justify-end gap-2 border-t border-border pt-5"><Button variant="ghost" onClick={onCancel}>Cancelar</Button><Button variant="primary" type="submit" disabled={saving||!pessoas.length||!disponiveis.length}>{saving?'Salvando…':item?'Salvar alterações':'Criar e enviar para aprovação'}</Button></div>
  </form>
}
