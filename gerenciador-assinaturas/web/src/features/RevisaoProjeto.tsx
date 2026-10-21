import type { Projeto, TecnologiaProjeto } from '../types'
import { reais } from '../lib/format'
import { Card } from '../components/ui/card'
import { cn } from '../lib/utils'

const APROVADO = { classe: 'bg-muted text-foreground', legenda: 'aprovado' }
const ESTILO: Record<string, typeof APROVADO> = {
  Proposto: { classe: 'bg-emerald-500/12 text-emerald-800 dark:text-emerald-200', legenda: 'entra' },
  'Remoção proposta': { classe: 'bg-red-500/8 text-red-700 line-through decoration-2 dark:text-red-300', legenda: 'sai' },
  Aprovado: APROVADO,
}

function Tecnologia({ tecnologia }: { tecnologia: TecnologiaProjeto }) {
  const estilo = ESTILO[tecnologia.situacao] ?? APROVADO
  return <li className={cn('flex items-center justify-between gap-3 rounded-lg px-3 py-1.5 text-sm', estilo.classe)}>
    <span className="min-w-0 truncate font-medium">{tecnologia.nome}<span className="sr-only"> ({estilo.legenda})</span></span>
    <span className="shrink-0 tabular-nums text-xs opacity-80">{reais(Number(tecnologia.mensal) || 0)}/mês</span>
  </li>
}

export function RevisaoProjeto({ projeto }: { projeto: Projeto }) {
  const linhas = projeto.equipe.flatMap((membro) => membro.assinaturas)
  const entram = linhas.filter((t) => t.situacao === 'Proposto').length
  const saem = linhas.filter((t) => t.situacao === 'Remoção proposta').length
  const temMudanca = entram + saem > 0
  return <div className="space-y-5">
    <div className="grid gap-3 sm:grid-cols-3">
      <Card className="p-4"><p className="text-xs text-muted-foreground">Pessoas</p><p className="mt-1 text-xl font-bold">{projeto.equipe.length}</p></Card>
      <Card className="p-4"><p className="text-xs text-muted-foreground">Tecnologias</p><p className="mt-1 text-xl font-bold">{projeto.assinaturas_ids.length}</p></Card>
      <Card className="p-4"><p className="text-xs text-muted-foreground">Custo mensal aprovado</p><p className="mt-1 text-xl font-bold">{reais(projeto['Custo mensal'] || 0)}</p></Card>
    </div>
    {temMudanca && <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
      {entram > 0 && <span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-full bg-emerald-500" />{entram} entra{entram === 1 ? '' : 'm'}</span>}
      {saem > 0 && <span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-full bg-red-500" />{saem} sai{saem === 1 ? '' : 'em'} após aprovação</span>}
      <span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-full bg-muted-foreground/40" />já aprovado</span>
    </div>}
    <div className="overflow-hidden rounded-xl border border-border">
      <table className="w-full text-left text-sm">
        <thead className="bg-muted/60 text-xs uppercase text-muted-foreground"><tr><th scope="col" className="px-4 py-2.5 font-semibold">Pessoa</th><th scope="col" className="px-4 py-2.5 font-semibold">Tecnologias</th></tr></thead>
        <tbody className="divide-y divide-border">
          {projeto.equipe.map((membro) => <tr key={membro.pessoa_id} className="align-top">
            <td className="w-2/5 px-4 py-3"><p className="font-semibold">{membro.nome}</p><p className="mt-0.5 break-all text-xs text-muted-foreground">{[membro.departamento, membro.email].filter(Boolean).join(' · ')}</p></td>
            <td className="px-4 py-3"><ul className="space-y-1.5">{membro.assinaturas.map((t) => <Tecnologia key={`${t.id}-${t.situacao}`} tecnologia={t} />)}</ul></td>
          </tr>)}
          {!projeto.equipe.length && <tr><td colSpan={2} className="px-4 py-8 text-center text-muted-foreground">Nenhuma pessoa na equipe.</td></tr>}
        </tbody>
      </table>
    </div>
  </div>
}
