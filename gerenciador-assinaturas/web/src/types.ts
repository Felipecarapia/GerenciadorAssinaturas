export type JsonRecord = Record<string, any>

export type Perfil = 'financeiro' | 'suporte'

export interface Usuario { nome: string; email: string; perfil: Perfil }
export interface Sessao { autenticado: boolean; modo_local: boolean; usuario: Usuario }

export interface Indicadores {
  total_ativas: number
  gasto_mensal: number
  gasto_anual: number
  vencendo_30: number
  vencidas: number
  colaboradores: number
}

export interface UsoAssinatura { pessoa_id: string; pessoa: string; projeto_id: string; projeto: string }

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
  usada_por: UsoAssinatura[]
}

export interface Pessoa extends JsonRecord {
  ID: string
  'Nome completo': string
  'E-mail': string
  Departamento: string
  Cargo: string
  Assinaturas: string
  'Cadastrado em': string | null
  assinaturas_lista: string[]
  projetos_lista: string[]
  'Custo mensal': number
}

export interface PessoaProjeto extends Pessoa { assinaturas_ids: string[] }
export interface MembroProjeto { pessoa_id: string; assinaturas_ids: string[] }

export interface TecnologiaProjeto {
  id: string
  nome: string
  situacao: 'Aprovado' | 'Proposto' | 'Remoção proposta' | 'Encerrado'
  mensal: number
}

export interface EquipeProjeto {
  pessoa_id: string
  nome: string
  email: string
  departamento: string
  assinaturas: TecnologiaProjeto[]
}

export interface Projeto extends JsonRecord {
  ID: string
  Nome: string
  Cliente: string
  'Responsável': string
  Departamento: string
  Status: 'Pendente' | 'Recusado' | 'Ativo' | 'Concluído'
  'Observações': string
  Assinaturas: number
  'Custo mensal': number
  'Custo anual': number
  assinaturas_ids: string[]
  equipe: EquipeProjeto[]
  Pessoas: number
  'Motivo da recusa': string
  'Solicitado por': string
  'Solicitado em': string | null
  'Aprovado por': string
  'Aprovado em': string | null
  'Recusado por': string
  'Recusado em': string | null
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
