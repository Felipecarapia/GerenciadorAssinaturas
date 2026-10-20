import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { CalendarClock, CalendarDays, CreditCard, FileText, Layers, TrendingDown, TrendingUp, Wallet } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../lib/api'
import { data, reais } from '../lib/format'
import { cn } from '../lib/utils'
import type { Assinatura, Indicadores } from '../types'
import { ErrorBanner, Loading } from '../components/Page'
import { Card } from '../components/ui/card'

// Escala institucional do IRT, aplicada também a gráficos e indicadores.
const escala = ['var(--marca-3)', 'var(--marca-4)', 'var(--marca-5)', 'var(--marca-1)', 'var(--marca-2)', 'var(--marca-6)']

interface DashboardData {
  indicadores: Indicadores
  evolucao: Array<{ 'Mês': string; 'Gasto mensal': number }>
  categorias: Array<{ Categoria: string; 'Gasto mensal': number }>
  status: Array<{ Status: string; Quantidade: number }>
  top: Array<{ Nome: string; 'Gasto mensal': number; Plano?: string }>
  alertas: Assinatura[]
}

const plural = (n: number, um: string, varios: string) => `${n} ${n === 1 ? um : varios}`
const percentual = (valor: number) => `${valor > 0 ? '+' : ''}${valor.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
const corNivel = { vermelho: 'var(--urgente)', amarelo: 'var(--atencao)', verde: 'var(--em-dia)', nenhum: 'var(--muted-foreground)' }

function Marca({ item, tamanho = 36 }: { item: Assinatura; tamanho?: number }) {
  const [semLogo, setSemLogo] = useState(!item['Logo (URL)'])
  return (
    <span className="grid shrink-0 place-items-center overflow-hidden rounded-xl bg-white font-display font-semibold text-[#172334] ring-1 ring-border" style={{ width: tamanho, height: tamanho, fontSize: tamanho * 0.4 }}>
      {semLogo ? item.Nome.slice(0, 1).toUpperCase() : <img src={item['Logo (URL)']!} alt="" width={tamanho} height={tamanho} loading="lazy" className="size-[62%] object-contain" onError={() => setSemLogo(true)} />}
    </span>
  )
}

function Variacao({ valor, claro = false }: { valor: number | null; claro?: boolean }) {
  if (valor === null) return null
  const Icone = valor >= 0 ? TrendingUp : TrendingDown
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums transition-colors duration-200', claro ? 'bg-primary/10 text-primary dark:group-hover:bg-white/20 dark:group-hover:text-white' : valor > 0 ? 'bg-urgente/12 text-urgente' : 'bg-em-dia/12 text-em-dia')}>
      <Icone aria-hidden="true" className="size-3" />{percentual(valor)}
    </span>
  )
}

function MarcaDaguaCard() {
  return <img src="/logo_reconcavo.png" alt="" width="224" height="128" aria-hidden="true" className="pointer-events-none absolute -right-6 -bottom-2 h-32 w-56 object-contain opacity-0 mix-blend-luminosity transition-opacity duration-200 group-hover:opacity-[.14]" />
}

function Indicador({ titulo, valor, icone, cor, rodape, destaque = false, children }: { titulo: string; valor: ReactNode; icone: ReactNode; cor?: string; rodape: ReactNode; destaque?: boolean; children?: ReactNode }) {
  return (
    <Card data-testid={destaque ? 'featured-metric' : undefined} className={cn('group relative flex min-h-36 flex-col overflow-hidden p-5 transition-[transform,border-color,box-shadow] duration-200 hover:-translate-y-0.5 hover:shadow-[var(--shadow-card-hover)] sm:min-h-44', destaque && 'hover:border-primary/40')}>
      {destaque && <span data-testid="featured-metric-accent" aria-hidden="true" className="pointer-events-none absolute inset-0 bg-[var(--gradiente-marca)] opacity-0 transition-opacity duration-200 group-hover:opacity-100" />}
      <MarcaDaguaCard />
      <span aria-hidden="true" className={cn('relative z-[1] grid size-10 place-items-center rounded-xl text-white transition-colors duration-200', destaque ? 'bg-primary dark:group-hover:bg-white/20' : '')} style={destaque ? undefined : { background: cor }}>{icone}</span>
      <p className={cn('relative z-[1] mt-auto pt-5 text-sm transition-colors duration-200', destaque ? 'text-muted-foreground dark:group-hover:text-white/80' : 'text-muted-foreground')}>{titulo}</p>
      <div className="relative z-[1] mt-1 flex flex-wrap items-center gap-2">
        <p className="font-display text-[1.75rem] leading-tight font-semibold tracking-[-0.02em] tabular-nums">{valor}</p>
        {children}
      </div>
      <p className={cn('relative z-[1] mt-1 text-xs transition-colors duration-200', destaque ? 'text-muted-foreground dark:group-hover:text-white/75' : 'text-muted-foreground')}>{rodape}</p>
    </Card>
  )
}

function DicaGrafico({ active, payload, label }: { active?: boolean; payload?: ReadonlyArray<{ value?: unknown }>; label?: unknown }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-border bg-card px-3.5 py-2.5 shadow-xl">
      <p className="text-xs text-muted-foreground">{String(label)}</p>
      <p className="mt-0.5 font-display text-base font-semibold tabular-nums">{reais(Number(payload[0]?.value))}</p>
    </div>
  )
}

function Evolucao({ evolucao }: { evolucao: DashboardData['evolucao'] }) {
  const valores = evolucao.map((e) => e['Gasto mensal'])
  const media = valores.length ? valores.reduce((a, b) => a + b, 0) / valores.length : 0
  const pico = evolucao.reduce<DashboardData['evolucao'][number] | null>((maior, e) => (!maior || e['Gasto mensal'] > maior['Gasto mensal'] ? e : maior), null)

  return (
    <Card className="group relative flex flex-col overflow-hidden p-5 sm:p-6">
      <MarcaDaguaCard />
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-lg font-semibold tracking-tight">Evolução do gasto</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">Gasto mensal ao fim de cada um dos últimos 12 meses</p>
        </div>
        <dl className="flex gap-6 sm:text-right">
          <div><dt className="text-xs text-muted-foreground">Média</dt><dd className="font-display font-semibold tabular-nums">{reais(media)}</dd></div>
          {pico && <div><dt className="text-xs text-muted-foreground">Maior, em {pico['Mês']}</dt><dd className="font-display font-semibold tabular-nums">{reais(pico['Gasto mensal'])}</dd></div>}
        </dl>
      </div>
      <div className="mt-6 h-72 xl:h-auto xl:min-h-72 xl:flex-1" role="img" aria-label={`Gráfico do gasto mensal nos últimos ${evolucao.length} meses. Média de ${reais(media)}${pico ? ` e maior valor de ${reais(pico['Gasto mensal'])} em ${pico['Mês']}` : ''}.`}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={evolucao} margin={{ left: 0, right: 6, top: 10 }}>
            <defs>
              <linearGradient id="evolucao-preenchimento" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--marca-5)" stopOpacity={0.45} />
                <stop offset="100%" stopColor="var(--marca-3)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="evolucao-linha" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="var(--marca-3)" />
                <stop offset="100%" stopColor="var(--marca-5)" />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 6" vertical={false} />
            <XAxis dataKey="Mês" tickLine={false} axisLine={false} tickMargin={10} />
            <YAxis tickFormatter={(v) => `${(v / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mil`} tickLine={false} axisLine={false} width={52} />
            <Tooltip content={(p) => <DicaGrafico active={p.active} payload={p.payload} label={p.label} />} cursor={{ stroke: 'var(--muted-foreground)', strokeDasharray: '4 4' }} />
            <Area type="monotone" dataKey="Gasto mensal" stroke="url(#evolucao-linha)" strokeWidth={2.5} fill="url(#evolucao-preenchimento)" activeDot={{ r: 5, fill: 'var(--card)', stroke: 'var(--marca-5)', strokeWidth: 3 }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

function Distribuicao({ categorias, top }: { categorias: DashboardData['categorias']; top: DashboardData['top'] }) {
  const [aba, setAba] = useState<'categorias' | 'top'>('categorias')
  const total = categorias.reduce((s, c) => s + c['Gasto mensal'], 0) || 1
  const maiorTop = Math.max(1, ...top.map((t) => t['Gasto mensal']))
  const linhas = aba === 'categorias'
    ? categorias.slice(0, 6).map((c) => ({ nome: c.Categoria, fracao: c['Gasto mensal'] / total, rotulo: `${Math.round((c['Gasto mensal'] / total) * 100)}%` }))
    : top.map((t) => ({ nome: t.Nome, fracao: t['Gasto mensal'] / maiorTop, rotulo: reais(t['Gasto mensal']) }))

  return (
    <Card className="group relative flex flex-col overflow-hidden p-5 sm:p-6">
      <MarcaDaguaCard />
      <h2 className="font-display text-lg font-semibold tracking-tight">Para onde vai o dinheiro</h2>
      <div role="tablist" aria-label="Agrupar gasto" className="mt-4 grid grid-cols-2 gap-1 rounded-xl bg-muted p-1">
        {([['categorias', 'Por categoria'], ['top', 'Mais caras']] as const).map(([id, rotulo]) => (
          <button key={id} id={`gastos-tab-${id}`} role="tab" aria-controls="gastos-painel" aria-selected={aba === id} tabIndex={aba === id ? 0 : -1} onClick={() => setAba(id)} className={cn('h-8 rounded-lg text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring', aba === id ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground')}>{rotulo}</button>
        ))}
      </div>
      <ul id="gastos-painel" role="tabpanel" aria-labelledby={`gastos-tab-${aba}`} className="mt-5 flex flex-1 flex-col justify-between gap-4">
        {!linhas.length && <li className="text-sm text-muted-foreground">Cadastre assinaturas ativas com valor para ver a distribuição.</li>}
        {linhas.map((linha, i) => (
          <li key={linha.nome}>
            <div className="flex items-center gap-3 text-sm">
              <span className="grid size-7 shrink-0 place-items-center rounded-lg text-[11px] font-bold text-white" style={{ background: escala[i % escala.length] }}>{aba === 'top' ? i + 1 : linha.nome.slice(0, 1)}</span>
              <span className="flex-1 truncate font-medium">{linha.nome}</span>
              <span className="font-semibold tabular-nums">{linha.rotulo}</span>
            </div>
            <div role="progressbar" aria-label={`${linha.nome}: ${linha.rotulo}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(linha.fracao * 100)} className="mt-2 ml-10 h-2 overflow-hidden rounded-full bg-muted">
              <div className="h-full rounded-full" style={{ width: `${Math.max(3, linha.fracao * 100)}%`, background: 'var(--gradiente-marca)' }} />
            </div>
          </li>
        ))}
      </ul>
    </Card>
  )
}

function Alertas({ alertas }: { alertas: Assinatura[] }) {
  const [nivel, setNivel] = useState<'vermelho' | 'amarelo' | 'verde' | 'todos'>('vermelho')
  const contagem = (valor: string) => alertas.filter((item) => item.nivel === valor).length
  const linhas = (nivel === 'todos' ? alertas : alertas.filter((item) => item.nivel === nivel)).slice(0, 8)
  const filtros = [
    { id: 'vermelho', rotulo: 'Urgentes', n: contagem('vermelho') },
    { id: 'amarelo', rotulo: 'Atenção', n: contagem('amarelo') },
    { id: 'verde', rotulo: 'Em dia', n: contagem('verde') },
    { id: 'todos', rotulo: 'Todas', n: alertas.length },
  ] as const

  return (
    <Card className="group relative mt-5 overflow-hidden">
      <MarcaDaguaCard />
      <div className="flex flex-col gap-4 p-5 sm:p-6 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="font-display text-lg font-semibold tracking-tight">Alertas de vencimento</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">Urgente: vence em até 7 dias ou já venceu. Atenção: vence de 8 a 30 dias.</p>
        </div>
        <div role="group" aria-label="Filtrar alertas" className="flex flex-wrap gap-1 self-start rounded-xl bg-muted p-1">
          {filtros.map((f) => (
            <button key={f.id} aria-pressed={nivel === f.id} onClick={() => setNivel(f.id)} className={cn('flex h-8 items-center gap-1.5 rounded-lg px-3 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring', nivel === f.id ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground')}>
              {f.rotulo}<span className="tabular-nums opacity-60">{f.n}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="relative overflow-x-auto" role="region" aria-label="Alertas de vencimento" tabIndex={0}>
        <table className="w-full min-w-[720px] text-sm">
          <caption className="sr-only">Assinaturas filtradas por situação de vencimento.</caption>
          <thead>
            <tr className="border-y border-border bg-muted/50 text-left text-xs text-muted-foreground">
              <th className="px-6 py-3 font-medium">Assinatura</th>
              <th className="px-4 py-3 font-medium">Valor</th>
              <th className="px-4 py-3 font-medium">Vencimento</th>
              <th className="px-4 py-3 font-medium">Situação</th>
              <th className="px-6 py-3"><span className="sr-only">Ações</span></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {!linhas.length && <tr><td colSpan={5} className="px-6 py-10 text-center text-muted-foreground">Nenhuma assinatura nesta faixa.</td></tr>}
            {linhas.map((item) => (
              <tr key={item.ID} className="transition-colors hover:bg-muted/40">
                <td className="px-6 py-3.5">
                  <div className="flex items-center gap-3">
                    <Marca item={item} />
                    <div className="min-w-0"><p className="truncate font-semibold">{item.Nome}</p><p className="text-xs text-muted-foreground">{item.Categoria || 'Sem categoria'}</p></div>
                  </div>
                </td>
                <td className="px-4 py-3.5"><p className="font-medium tabular-nums">{reais(item.valor_num)}</p><p className="text-xs text-muted-foreground">{item.Plano}</p></td>
                <td className="px-4 py-3.5 tabular-nums text-muted-foreground">{data(item.venc_data)}</td>
                <td className="px-4 py-3.5">
                  <span className="inline-flex items-center gap-2 rounded-full border border-border px-2.5 py-1 text-xs font-medium whitespace-nowrap">
                    <span className="size-2 rounded-full" style={{ background: corNivel[item.nivel] }} />{item.texto_alerta}
                  </span>
                </td>
                <td className="px-6 py-3.5 text-right"><Link to="/assinaturas" aria-label={`Abrir ${item.Nome}`} className="inline-flex h-8 items-center rounded-lg px-3 text-xs font-semibold text-muted-foreground ring-1 ring-border transition-colors hover:bg-muted hover:text-foreground">Abrir</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

export function DashboardPage() {
  useEffect(() => { document.title = 'Dashboard · Licenzy' }, [])
  const query = useQuery({ queryKey: ['dashboard'], queryFn: () => api<DashboardData>('/api/dashboard') })
  if (query.isLoading) return <Loading />
  if (query.isError) return <><h1 className="mb-4 font-display text-2xl font-semibold">Dashboard</h1><ErrorBanner message={(query.error as Error).message} onRetry={() => query.refetch()} /></>
  const d = query.data!
  const ind = d.indicadores
  const [anterior, atual] = d.evolucao.slice(-2).map((e) => e['Gasto mensal'])
  const variacaoMes = anterior && atual !== undefined ? ((atual - anterior) / anterior) * 100 : null
  const foraDasAtivas = d.status.filter((s) => s.Quantidade > 0 && !s.Status.toLocaleLowerCase('pt-BR').startsWith('ativ')).map((s) => `${s.Quantidade} ${s.Status.toLocaleLowerCase('pt-BR')}`)
  const hoje = new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date())

  return (
    <>
      <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <h1 className="font-display text-[1.75rem] font-semibold tracking-[-0.02em] sm:text-3xl">Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">Quanto se gasta com software, quem usa e o que vence em breve.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex h-10 items-center gap-2 rounded-[var(--radius-sm)] border border-border bg-card px-3.5 text-sm"><CalendarDays aria-hidden="true" className="size-4 text-muted-foreground" />{hoje}</span>
          <Link to="/relatorios" className="inline-flex h-10 items-center gap-2 rounded-[var(--radius-sm)] bg-primary px-4 text-sm font-semibold text-white transition-colors hover:bg-primary-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"><FileText aria-hidden="true" className="size-4" />Gerar relatório</Link>
        </div>
      </div>

      <section className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        <Indicador destaque titulo="Gasto mensal" valor={reais(ind.gasto_mensal)} icone={<Wallet className="size-5" />} rodape="Variação em relação ao mês anterior">
          <Variacao valor={variacaoMes} claro />
        </Indicador>
        <Indicador titulo="Gasto anual" valor={reais(ind.gasto_anual)} cor="var(--marca-3)" icone={<CreditCard className="size-5" />} rodape={ind.colaboradores ? `${reais(ind.gasto_anual / ind.colaboradores)} por colaborador` : 'Sem colaboradores cadastrados'} />
        <Indicador titulo="Assinaturas ativas" valor={ind.total_ativas} cor="var(--marca-5)" icone={<Layers className="size-5" />} rodape={foraDasAtivas.length ? `Fora das ativas: ${foraDasAtivas.join(', ')}` : plural(ind.colaboradores, 'colaborador usa', 'colaboradores usam')} />
        <Indicador titulo="Vencem em 30 dias" valor={ind.vencendo_30} cor="var(--marca-1)" icone={<CalendarClock className="size-5" />} rodape={ind.vencidas ? 'Renove as vencidas para não perder acesso' : 'Nenhuma assinatura vencida'}>
          {ind.vencidas > 0 && <span className="rounded-full bg-urgente/12 px-2 py-0.5 text-xs font-semibold text-urgente">{plural(ind.vencidas, 'vencida', 'vencidas')}</span>}
        </Indicador>
      </section>

      <section className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Evolucao evolucao={d.evolucao} />
        <Distribuicao categorias={d.categorias} top={d.top} />
      </section>

      <Alertas alertas={d.alertas} />
    </>
  )
}
