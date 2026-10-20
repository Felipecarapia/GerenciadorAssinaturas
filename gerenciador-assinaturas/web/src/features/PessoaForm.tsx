import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { z } from 'zod'
import { ApiError } from '../lib/api'
import type { Assinatura, Listas, Pessoa } from '../types'
import { Button } from '../components/ui/button'
import { Field, Input, MultiCheck, Select } from '../components/ui/form'

const schema = z.object({
  nome: z.string().trim().min(1, 'Informe o nome completo.'),
  email: z.email('Informe um e-mail válido.'),
  departamento: z.string().min(1, 'Escolha o departamento.'),
  cargo: z.string(),
  assinaturas: z.array(z.string()),
})
export type PessoaValores = z.infer<typeof schema>

export function PessoaForm({ item, listas, assinaturas, saving, serverError, onSubmit, onCancel }: { item?: Pessoa | null; listas: Listas; assinaturas: Assinatura[]; saving: boolean; serverError?: Error | null; onSubmit: (values: PessoaValores) => void; onCancel: () => void }) {
  const form = useForm<PessoaValores>({ resolver: zodResolver(schema), defaultValues: { nome: '', email: '', departamento: '', cargo: '', assinaturas: [] } })
  useEffect(() => { form.reset({ nome: item?.['Nome completo'] || '', email: item?.['E-mail'] || '', departamento: item?.Departamento || '', cargo: item?.Cargo || '', assinaturas: item?.assinaturas_lista || [] }) }, [item, form])
  useEffect(() => {
    if (!(serverError instanceof ApiError)) return
    const mapa: Record<string, keyof PessoaValores> = { 'Nome completo': 'nome', 'E-mail': 'email', Departamento: 'departamento' }
    Object.entries(serverError.fieldErrors).forEach(([campo, mensagem]) => mapa[campo] && form.setError(mapa[campo], { message: mensagem }))
  }, [serverError, form])
  const escolhidas = useWatch({ control: form.control, name: 'assinaturas' }) || []
  return <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
    {serverError && !(serverError instanceof ApiError && Object.keys(serverError.fieldErrors).length) && <div role="alert" aria-live="polite" className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-danger">{serverError.message} Revise os dados e tente novamente.</div>}
    <div className="grid gap-4 sm:grid-cols-2"><Field label="Nome completo" required error={form.formState.errors.nome?.message}><Input {...form.register('nome')} autoComplete="name" placeholder="Ex.: Ana Souza…" /></Field><Field label="E-mail" required error={form.formState.errors.email?.message}><Input {...form.register('email')} type="email" inputMode="email" autoComplete="email" spellCheck={false} placeholder="nome@empresa.com.br…" /></Field></div>
    <div className="grid gap-4 sm:grid-cols-2"><Field label="Departamento" required error={form.formState.errors.departamento?.message}><Select {...form.register('departamento')} autoComplete="organization"><option value="">Escolha</option>{listas.Departamentos.map((item)=><option key={item}>{item}</option>)}</Select></Field><Field label="Cargo"><Input {...form.register('cargo')} autoComplete="organization-title" placeholder="Ex.: Analista…" /></Field></div>
    <Field label="Assinaturas"><MultiCheck options={assinaturas.map((item)=>item.Nome)} selected={escolhidas} onChange={(value)=>form.setValue('assinaturas',value,{shouldValidate:true})}/></Field>
    <div className="flex flex-wrap justify-end gap-2 border-t border-border pt-5"><Button variant="ghost" onClick={onCancel}>Cancelar</Button><Button variant="primary" type="submit" disabled={saving} aria-busy={saving}>{saving?'Salvando…':'Salvar pessoa'}</Button></div>
  </form>
}
