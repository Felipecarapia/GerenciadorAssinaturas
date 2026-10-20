import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm,useWatch } from 'react-hook-form'
import { z } from 'zod'
import { ApiError } from '../lib/api'
import type { Assinatura, Listas, Projeto } from '../types'
import { Button } from '../components/ui/button'
import { Field, Input, MultiCheck, Select, Textarea } from '../components/ui/form'

const schema=z.object({nome:z.string().trim().min(1,'Informe o nome do projeto.'),cliente:z.string(),responsavel:z.string(),departamento:z.string(),status:z.string().min(1,'Escolha o status.'),assinaturas:z.array(z.string()).min(1,'Vincule pelo menos uma assinatura.'),observacoes:z.string()})
export type ProjetoValores=z.infer<typeof schema>

export function ProjetoForm({item,listas,assinaturas,saving,serverError,onSubmit,onCancel}:{item?:Projeto|null;listas:Listas;assinaturas:Assinatura[];saving:boolean;serverError?:Error|null;onSubmit:(v:ProjetoValores)=>void;onCancel:()=>void}){
  const form=useForm<ProjetoValores>({resolver:zodResolver(schema),defaultValues:{nome:'',cliente:'',responsavel:'',departamento:'',status:'Ativo',assinaturas:[],observacoes:''}})
  useEffect(()=>{form.reset({nome:item?.Nome||'',cliente:item?.Cliente||'',responsavel:item?.['Responsável']||'',departamento:item?.Departamento||'',status:item?.Status||'Ativo',assinaturas:item?.assinaturas_ids||[],observacoes:item?.['Observações']||''})},[item,form])
  useEffect(()=>{if(!(serverError instanceof ApiError))return;const mapa:Record<string,keyof ProjetoValores>={Nome:'nome',Status:'status',Assinaturas:'assinaturas'};Object.entries(serverError.fieldErrors).forEach(([c,m])=>mapa[c]&&form.setError(mapa[c],{message:m}))},[serverError,form])
  const escolhidas=useWatch({control:form.control,name:'assinaturas'})||[],labels=Object.fromEntries(assinaturas.map(a=>[a.ID,a.Nome]))
  return <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">{serverError&&!(serverError instanceof ApiError&&Object.keys(serverError.fieldErrors).length)&&<div role="alert" aria-live="polite" className="rounded-lg bg-red-500/10 p-3 text-sm text-danger">{serverError.message} Revise os dados e tente novamente.</div>}
    <div className="grid gap-4 sm:grid-cols-2"><Field label="Nome do projeto" required error={form.formState.errors.nome?.message}><Input {...form.register('nome')} autoComplete="off" placeholder="Ex.: Portal do cliente…"/></Field><Field label="Cliente"><Input {...form.register('cliente')} autoComplete="organization" placeholder="Ex.: Empresa…"/></Field></div>
    <div className="grid gap-4 sm:grid-cols-2"><Field label="Responsável"><Input {...form.register('responsavel')} autoComplete="name" placeholder="Ex.: Ana Souza…"/></Field><Field label="Departamento"><Select {...form.register('departamento')} autoComplete="organization"><option value="">Escolha</option>{listas.Departamentos.map(i=><option key={i}>{i}</option>)}</Select></Field></div>
    <Field label="Status" required error={form.formState.errors.status?.message}><Select {...form.register('status')} autoComplete="off"><option>Ativo</option><option>Pausado</option>{item?.Status==='Concluído'&&<option>Concluído</option>}</Select></Field>
    <Field label="Assinaturas usadas no projeto" required error={form.formState.errors.assinaturas?.message}><MultiCheck options={assinaturas.map(a=>a.ID)} labels={labels} selected={escolhidas} onChange={v=>form.setValue('assinaturas',v,{shouldValidate:true})}/></Field>
    <Field label="Observações"><Textarea {...form.register('observacoes')} autoComplete="off" placeholder="Inclua contexto útil para a equipe…"/></Field>
    <div className="flex flex-wrap justify-end gap-2 border-t border-border pt-5"><Button variant="ghost" onClick={onCancel}>Cancelar</Button><Button variant="primary" type="submit" disabled={saving} aria-busy={saving}>{saving?'Salvando…':'Salvar projeto'}</Button></div>
  </form>
}
