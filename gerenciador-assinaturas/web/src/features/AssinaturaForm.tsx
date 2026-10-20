import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { z } from 'zod'
import { ApiError } from '../lib/api'
import type { Assinatura, Listas, Pessoa } from '../types'
import { Button } from '../components/ui/button'
import { Field, Input, MultiCheck, Select } from '../components/ui/form'

const schema = z.object({
  nome: z.string().trim().min(1, 'Informe o nome.').max(80).refine((value) => !value.includes(','), 'O nome não pode ter vírgula.'),
  logo: z.string().trim().refine((value) => !value || /^https?:\/\//.test(value), 'Informe uma URL iniciada por https://'),
  categoria: z.string().min(1, 'Escolha a categoria.'),
  plano: z.string().min(1, 'Escolha o plano.'),
  valor: z.number().positive('O valor precisa ser maior que zero.'),
  vencimento: z.string(),
  status: z.string().min(1, 'Escolha o status.'),
  usuarios: z.array(z.string()).min(1, 'Escolha pelo menos uma pessoa.'),
}).superRefine((value, ctx) => {
  if (!value.plano.toLocaleLowerCase('pt-BR').includes('vital') && !value.vencimento) ctx.addIssue({ code: 'custom', path: ['vencimento'], message: 'Informe o vencimento.' })
})

export type AssinaturaValores = z.infer<typeof schema>

export function AssinaturaForm({ item, listas, pessoas, saving, serverError, onSubmit, onCancel }: { item?: Assinatura | null; listas: Listas; pessoas: Pessoa[]; saving: boolean; serverError?: Error | null; onSubmit: (values: AssinaturaValores) => void; onCancel: () => void }) {
  const form = useForm<AssinaturaValores>({
    resolver: zodResolver(schema),
    defaultValues: { nome: '', logo: '', categoria: '', plano: '', valor: 0, vencimento: '', status: 'Ativa', usuarios: [] },
  })
  useEffect(() => {
    form.reset({
      nome: item?.Nome || '', logo: item?.['Logo (URL)'] || '', categoria: item?.Categoria || '', plano: item?.Plano || '',
      valor: Number(item?.valor_num ?? item?.['Valor (R$)'] ?? 0), vencimento: item?.venc_data?.slice(0, 10) || '', status: item?.Status || 'Ativa', usuarios: item?.usuarios_ids || [],
    })
  }, [item, form])
  useEffect(() => {
    if (!(serverError instanceof ApiError)) return
    const mapa: Record<string, keyof AssinaturaValores> = { Nome: 'nome', 'Logo (URL)': 'logo', Categoria: 'categoria', Plano: 'plano', 'Valor (R$)': 'valor', Vencimento: 'vencimento', Status: 'status', Usuários: 'usuarios' }
    Object.entries(serverError.fieldErrors).forEach(([campo, mensagem]) => mapa[campo] && form.setError(mapa[campo], { message: mensagem }))
  }, [serverError, form])
  const selecionados = useWatch({ control: form.control, name: 'usuarios' }) || []
  const labels = Object.fromEntries(pessoas.map((pessoa) => [pessoa.ID, pessoa['Nome completo']]))
  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
      {serverError && !(serverError instanceof ApiError && Object.keys(serverError.fieldErrors).length) && <div role="alert" aria-live="polite" className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-danger">{serverError.message} Revise os dados e tente novamente.</div>}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Nome" required error={form.formState.errors.nome?.message}><Input {...form.register('nome')} autoComplete="off" placeholder="Ex.: Figma…" /></Field>
        <Field label="Categoria" required error={form.formState.errors.categoria?.message}><Select {...form.register('categoria')} autoComplete="off"><option value="">Escolha</option>{listas.Categorias.map((item) => <option key={item}>{item}</option>)}</Select></Field>
      </div>
      <Field label="Logo (URL)" error={form.formState.errors.logo?.message}><Input {...form.register('logo')} type="url" inputMode="url" autoComplete="off" spellCheck={false} placeholder="https://exemplo.com/logo.svg…" /></Field>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Field label="Plano" required error={form.formState.errors.plano?.message}><Select {...form.register('plano')} autoComplete="off"><option value="">Escolha</option>{listas.Planos.map((item) => <option key={item}>{item}</option>)}</Select></Field>
        <Field label="Valor (R$)" required error={form.formState.errors.valor?.message}><Input {...form.register('valor', { valueAsNumber: true })} type="number" inputMode="decimal" autoComplete="off" min="0" step="0.01" /></Field>
        <Field label="Vencimento" error={form.formState.errors.vencimento?.message}><Input {...form.register('vencimento')} type="date" autoComplete="off" min="2000-01-01" max="2100-12-31" /></Field>
        <Field label="Status" required error={form.formState.errors.status?.message}><Select {...form.register('status')} autoComplete="off">{listas.Status.map((item) => <option key={item}>{item}</option>)}</Select></Field>
      </div>
      <Field label="Usuários (mínimo 1)" required error={form.formState.errors.usuarios?.message}><MultiCheck options={pessoas.map((item) => item.ID)} labels={labels} selected={selecionados} onChange={(value) => form.setValue('usuarios', value, { shouldValidate: true })} /></Field>
      <p className="text-xs text-muted-foreground">O nome não pode ter vírgula: a planilha usa vírgula para separar as escolhas.</p>
      <div className="flex flex-wrap justify-end gap-2 border-t border-border pt-5"><Button variant="ghost" onClick={onCancel}>Cancelar</Button><Button variant="primary" type="submit" disabled={saving || !pessoas.length} aria-busy={saving}>{saving ? 'Salvando…' : 'Salvar assinatura'}</Button></div>
    </form>
  )
}
