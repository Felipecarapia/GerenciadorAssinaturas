import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { ApiError } from '../lib/api'
import { normalizar } from '../lib/format'
import type { Assinatura, Listas } from '../types'
import { Button } from '../components/ui/button'
import { Field, Input, Select } from '../components/ui/form'

const schema = z.object({
  nome: z.string().trim().min(1, 'Informe o nome.').max(80).refine((value) => !value.includes(','), 'O nome não pode ter vírgula.'),
  logo: z.string().trim().refine((value) => !value || /^https?:\/\//.test(value), 'Informe uma URL iniciada por https://'),
  categoria: z.string().min(1, 'Escolha a categoria.'),
  plano: z.string().min(1, 'Escolha o plano.'),
  valor: z.number().positive('O valor precisa ser maior que zero.'),
  vencimento: z.string(),
  status: z.string().min(1, 'Escolha o status.'),
}).superRefine((value, ctx) => {
  if (!value.plano.toLocaleLowerCase('pt-BR').includes('vital') && !value.vencimento) ctx.addIssue({ code: 'custom', path: ['vencimento'], message: 'Informe o vencimento.' })
})
export type AssinaturaValores = z.infer<typeof schema>

interface Props { item?: Assinatura | null; listas: Listas; saving: boolean; serverError?: Error | null; onSubmit: (values: AssinaturaValores) => void; onCancel: () => void }

export function AssinaturaForm({ item, listas, saving, serverError, onSubmit, onCancel }: Props) {
  const form = useForm<AssinaturaValores>({ resolver: zodResolver(schema), defaultValues: { nome: '', logo: '', categoria: '', plano: '', valor: 0, vencimento: '', status: 'Ativa' } })
  useEffect(() => { form.reset({ nome: item?.Nome || '', logo: item?.['Logo (URL)'] || '', categoria: item?.Categoria || '', plano: item?.Plano || '', valor: Number(item?.valor_num ?? item?.['Valor (R$)'] ?? 0), vencimento: item?.venc_data?.slice(0, 10) || '', status: item?.Status || 'Ativa' }) }, [item, form])
  useEffect(() => {
    if (!(serverError instanceof ApiError)) return
    const mapa: Record<string, keyof AssinaturaValores> = { Nome: 'nome', Categoria: 'categoria', Plano: 'plano', 'Valor (R$)': 'valor', Vencimento: 'vencimento', Status: 'status' }
    Object.entries(serverError.fieldErrors).forEach(([campo, mensagem]) => mapa[campo] && form.setError(mapa[campo], { message: mensagem }))
  }, [serverError, form])
  return <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
    {serverError && !(serverError instanceof ApiError && Object.keys(serverError.fieldErrors).length) && <div role="alert" className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-danger">{serverError.message}</div>}
    <div className="grid gap-4 sm:grid-cols-2"><Field label="Nome" required error={form.formState.errors.nome?.message}><Input {...form.register('nome')} /></Field><Field label="Categoria" required error={form.formState.errors.categoria?.message}><Select {...form.register('categoria')}><option value="">Escolha</option>{listas.Categorias.map((nome) => <option key={nome}>{nome}</option>)}</Select></Field></div>
    <Field label="Logo (URL)" error={form.formState.errors.logo?.message}><Input {...form.register('logo')} type="url" /></Field>
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><Field label="Plano" required error={form.formState.errors.plano?.message}><Select {...form.register('plano')}><option value="">Escolha</option>{listas.Planos.map((nome) => <option key={nome}>{nome}</option>)}</Select></Field><Field label="Valor (R$)" required error={form.formState.errors.valor?.message}><Input {...form.register('valor', { valueAsNumber: true })} type="number" min="0" step="0.01" /></Field><Field label="Vencimento" error={form.formState.errors.vencimento?.message}><Input {...form.register('vencimento')} type="date" /></Field><Field label="Status" required error={form.formState.errors.status?.message}><Select {...form.register('status')}>{listas.Status.map((nome) => <option key={nome}>{nome}</option>)}</Select></Field></div>
    {item && <div className="rounded-xl border border-border bg-muted/45 p-4"><p className="text-sm font-semibold">Usada por</p><p className="mt-1 text-xs text-muted-foreground">Os vínculos são administrados nos projetos.</p><div className="mt-3 space-y-2">{item.usada_por?.map((uso) => <p key={`${uso.projeto_id}-${uso.pessoa_id}`} className="text-sm"><strong>{uso.pessoa}</strong> · {uso.projeto}</p>)}{!item.usada_por?.length && (normalizar(item.Status) === 'ativa' ? <p className="text-sm text-amber-700 dark:text-amber-300">Não está em nenhum projeto ativo.</p> : <p className="text-sm text-muted-foreground">Ninguém usa esta assinatura em projeto ativo.</p>)}</div></div>}
    <div className="flex justify-end gap-2 border-t border-border pt-5"><Button variant="ghost" onClick={onCancel}>Cancelar</Button><Button variant="primary" type="submit" disabled={saving}>{saving ? 'Salvando…' : 'Salvar assinatura'}</Button></div>
  </form>
}
