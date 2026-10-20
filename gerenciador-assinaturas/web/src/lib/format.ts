export const reais = (valor: number | string | null | undefined) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(valor || 0))

export const data = (valor: string | null | undefined) => {
  if (!valor) return '—'
  const iso = /^\d{4}-\d{2}-\d{2}$/.test(valor) ? `${valor}T12:00:00` : valor
  const parsed = new Date(iso)
  return Number.isNaN(parsed.getTime()) ? String(valor) : new Intl.DateTimeFormat('pt-BR').format(parsed)
}

export const dataHora = (valor: string | null | undefined) => {
  if (!valor) return '—'
  const parsed = new Date(valor.includes('T') ? valor : valor.replace(' ', 'T'))
  return Number.isNaN(parsed.getTime())
    ? String(valor)
    : new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(parsed)
}

export const normalizar = (valor: unknown) =>
  String(valor ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR')
    .trim()

export const iniciais = (nome: string) =>
  nome.split(/\s+/).filter(Boolean).slice(0, 2).map((parte) => parte[0]).join('').toUpperCase()
