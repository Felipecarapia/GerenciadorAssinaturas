export const reais = (valor: number | string | null | undefined) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(valor || 0))

const MILISSEGUNDOS_POR_DIA = 86_400_000
const EPOCA_GOOGLE_SHEETS = Date.UTC(1899, 11, 30)

const dataDoGoogleSheets = (valor: number) => {
  const utc = new Date(EPOCA_GOOGLE_SHEETS + valor * MILISSEGUNDOS_POR_DIA)
  return new Date(
    utc.getUTCFullYear(), utc.getUTCMonth(), utc.getUTCDate(),
    utc.getUTCHours(), utc.getUTCMinutes(), utc.getUTCSeconds(), utc.getUTCMilliseconds(),
  )
}

export const data = (valor: unknown) => {
  if (!valor) return '—'
  const texto = String(valor)
  const iso = /^\d{4}-\d{2}-\d{2}$/.test(texto) ? `${texto}T12:00:00` : texto
  const parsed = typeof valor === 'number' ? dataDoGoogleSheets(valor) : new Date(iso)
  return Number.isNaN(parsed.getTime()) ? String(valor) : new Intl.DateTimeFormat('pt-BR').format(parsed)
}

export const dataHora = (valor: unknown) => {
  if (!valor) return '—'
  const texto = String(valor)
  const parsed = typeof valor === 'number'
    ? dataDoGoogleSheets(valor)
    : new Date(texto.includes('T') ? texto : texto.replace(' ', 'T'))
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
