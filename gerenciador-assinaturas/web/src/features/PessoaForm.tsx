import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { ApiError } from '../lib/api'
import type { Listas, Pessoa } from '../types'
import { Button } from '../components/ui/button'
import { Field, Input, Select } from '../components/ui/form'

const schema = z.object({
  nome: z.string().trim().min(1, 'Informe o nome completo.'),
  email: z.email('Informe um e-mail válido.'),
  departamento: z.string().min(1, 'Escolha o departamento.'),
  cargo: z.string(),
})
export type PessoaValores = z.infer<typeof schema>

interface Props {
  item?: Pessoa | null
  listas: Listas
  saving: boolean
  serverError?: Error | null
  onSubmit: (values: PessoaValores) => void
  onCancel: () => void
}

export function PessoaForm({ item, listas, saving, serverError, onSubmit, onCancel }: Props) {
  const form = useForm<PessoaValores>({ resolver: zodResolver(schema), defaultValues: { nome: '', email: '', departamento: '', cargo: '' } })
  useEffect(() => { form.reset({ nome: item?.['Nome completo'] || '', email: item?.['E-mail'] || '', departamento: item?.Departamento || '', cargo: item?.Cargo || '' }) }, [item, form])
  useEffect(() => {
    if (!(serverError instanceof ApiError)) return
    const mapa: Record<string, keyof PessoaValores> = { 'Nome completo': 'nome', 'E-mail': 'email', Departamento: 'departamento' }
    Object.entries(serverError.fieldErrors).forEach(([campo, mensagem]) => mapa[campo] && form.setError(mapa[campo], { message: mensagem }))
  }, [serverError, form])
  return <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
    {serverError && !(serverError instanceof ApiError && Object.keys(serverError.fieldErrors).length) && <div role="alert" className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-danger">{serverError.message}</div>}
    <div className="grid gap-4 sm:grid-cols-2"><Field label="Nome completo" required error={form.formState.errors.nome?.message}><Input {...form.register('nome')} autoComplete="name" /></Field><Field label="E-mail" required error={form.formState.errors.email?.message}><Input {...form.register('email')} type="email" autoComplete="email" /></Field></div>
    <div className="grid gap-4 sm:grid-cols-2"><Field label="Departamento" required error={form.formState.errors.departamento?.message}><Select {...form.register('departamento')}><option value="">Escolha</option>{listas.Departamentos.map((nome) => <option key={nome}>{nome}</option>)}</Select></Field><Field label="Cargo"><Input {...form.register('cargo')} autoComplete="organization-title" /></Field></div>
    <p className="rounded-xl border border-border bg-muted/50 px-4 py-3 text-sm text-muted-foreground">As assinaturas são definidas na equipe de cada projeto e aparecem aqui automaticamente após aprovação.</p>
    <div className="flex justify-end gap-2 border-t border-border pt-5"><Button variant="ghost" onClick={onCancel}>Cancelar</Button><Button variant="primary" type="submit" disabled={saving}>{saving ? 'Salvando…' : 'Salvar pessoa'}</Button></div>
  </form>
}
