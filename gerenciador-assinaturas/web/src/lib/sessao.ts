import { useQuery } from '@tanstack/react-query'
import { api } from './api'
import type { Sessao } from '../types'

export function useSessao() {
  return useQuery({ queryKey: ['sessao'], queryFn: () => api<Sessao>('/api/sessao'), staleTime: 60_000 })
}

/** Decide só o que mostrar; quem autoriza a ação é o servidor. */
export function useEhFinanceiro() {
  return useSessao().data?.usuario.perfil === 'financeiro'
}
