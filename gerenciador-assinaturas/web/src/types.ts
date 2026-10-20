export type JsonRecord = Record<string, any>

export interface Indicadores {
  total_ativas: number
  gasto_mensal: number
  gasto_anual: number
  vencendo_30: number
  vencidas: number
  colaboradores: number
}

export interface Assinatura extends JsonRecord {
  ID: string
  Nome: string
  'Logo (URL)': string | null
  Categoria: string
  Plano: string
  'Valor (R$)': number | string
  Vencimento: string | null
  Status: string
  valor_num: number
  mensal: number
  venc_data: string | null
  dias: number | null
  nivel: 'vermelho' | 'amarelo' | 'verde' | 'nenhum'
  alerta: string
  texto_alerta: string
  usuarios_ids: string[]
  projetos: string[]
}

export interface Pessoa extends JsonRecord {
  ID: string
  'Nome completo': string
  'E-mail': string
  Departamento: string
  Cargo: string
  Assinaturas: string
  assinaturas_lista: string[]
  'Custo mensal': number
}

export interface Projeto extends JsonRecord {
  ID: string
  Nome: string
  Cliente: string
  'Responsável': string
  Departamento: string
  Status: string
  'Observações': string
  Assinaturas: number
  'Custo mensal': number
  'Custo anual': number
  assinaturas_ids: string[]
}

export interface Historico extends JsonRecord {
  'Data e hora': string
  Origem: string
  Quem: string
  Assinatura: string
  Evento: string
  Campo: string
  'Valor anterior': string
  'Valor novo': string
  _quando: string | null
}

export interface Pendencia extends JsonRecord {
  Aba: string
  Linha: number
  ID: string
  Tipo: string
  Descricao?: string
  'Descrição': string
  Item: string
}

export interface Listas {
  Categorias: string[]
  Departamentos: string[]
  Planos: string[]
  Status: string[]
}
