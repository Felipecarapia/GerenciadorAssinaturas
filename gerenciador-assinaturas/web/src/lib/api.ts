import { toast } from 'sonner'

export class ApiError extends Error {
  status: number
  fieldErrors: Record<string, string>
  tentativasRestantes?: number
  tenteEmSegundos?: number

  constructor(status: number, detail: any) {
    const message = typeof detail === 'string'
      ? detail
      : detail?.mensagem || detail?.message || Object.values(detail?.erros || {})[0] || 'Não foi possível concluir a operação.'
    super(String(message))
    this.name = 'ApiError'
    this.status = status
    this.fieldErrors = detail?.erros || {}
    this.tentativasRestantes = typeof detail?.tentativas_restantes === 'number' ? detail.tentativas_restantes : undefined
    this.tenteEmSegundos = typeof detail?.tente_em_segundos === 'number' ? detail.tente_em_segundos : undefined
  }
}

async function errorPayload(response: Response) {
  try { return await response.json() } catch { return await response.text() }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(path, { ...init, headers, credentials: 'include' })
  if (response.status === 401 && path !== '/api/login') {
    if (window.location.pathname !== '/login') window.location.assign('/login')
    throw new ApiError(401, 'Sua sessão terminou. Entre novamente.')
  }
  if (!response.ok) {
    const payload: any = await errorPayload(response)
    if (response.status === 403) {
      toast.error(payload?.detail || 'Seu perfil não permite esta ação.')
    }
    throw new ApiError(response.status, payload?.detail ?? payload)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function baixar(path: string, nomePadrao: string) {
  const response = await fetch(path, { credentials: 'include' })
  if (!response.ok) {
    const payload: any = await errorPayload(response)
    throw new ApiError(response.status, payload?.detail ?? payload)
  }
  const blob = await response.blob()
  const disposition = response.headers.get('content-disposition') || ''
  const nome = disposition.match(/filename="?([^";]+)"?/i)?.[1] || nomePadrao
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = nome
  link.click()
  URL.revokeObjectURL(url)
}
