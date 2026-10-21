import { useMutation } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { ArrowRight, Eye, EyeOff, LockKeyhole, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { ApiError, api } from '../lib/api'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/form'
import { KineticGrid } from '../components/ui/kinetic-grid'

function InstitutionalLogo({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`flex aspect-[16/9] items-center ${compact ? 'w-[50px] max-w-full' : 'w-[160px] max-w-full'}`}>
      <img src="/logo_reconcavo.png" alt="Instituto Recôncavo de Tecnologia" width="440" height="248" fetchPriority="high" className="h-full w-full object-contain" />
    </div>
  )
}

export function LoginPage() {
  const navigate = useNavigate()
  const [senha, setSenha] = useState('')
  const [mostrar, setMostrar] = useState(false)
  useEffect(() => { document.title = 'Entrar · Licenzy' }, [])
  useEffect(() => {
    api('/api/sessao').then(() => navigate({ to: '/' })).catch(() => undefined)
  }, [navigate])
  const login = useMutation({
    mutationFn: () => api<{ autenticado: boolean; modo_demo: boolean }>('/api/login', { method: 'POST', body: JSON.stringify({ senha }) }),
    onSuccess: () => navigate({ to: '/' }),
  })
  const erro = login.error instanceof ApiError ? login.error : null
  return (
    <main className="grid min-h-screen bg-white lg:h-screen lg:grid-cols-[minmax(0,1.08fr)_minmax(460px,.92fr)] lg:overflow-hidden">
      <section className="relative hidden min-h-screen overflow-hidden bg-white text-[#172334] lg:block lg:h-screen lg:min-h-0">
        <KineticGrid tone="light">
          <div className="flex h-full flex-col p-8 xl:p-10">
            <div className="flex w-full flex-1 flex-col items-center justify-center text-center">
              <div className="mb-10">
                <InstitutionalLogo />
              </div>
              <p className="mb-4 text-xs font-semibold uppercase tracking-[0.2em] text-[#25649a]">Gestão corporativa de licenças</p>
              <h2 className="max-w-[680px] text-4xl font-semibold leading-[1.12] tracking-[-0.035em] xl:text-5xl">Visibilidade para decidir. Controle para economizar.</h2>
            </div>
            <p className="mt-auto text-xs text-[#64748b]">Uma solução do Instituto Recôncavo de Tecnologia</p>
          </div>
        </KineticGrid>
      </section>
      <section className="relative flex min-h-screen items-center justify-center bg-[#102c50] px-5 pb-8 pt-48 text-white lg:h-screen lg:min-h-0 lg:rounded-l-[2rem] lg:px-10 lg:py-8 xl:rounded-l-[3rem]">
        <div className="absolute inset-x-0 top-0 flex h-44 items-center bg-white px-5 lg:hidden"><InstitutionalLogo compact /></div>
        <div className="w-full max-w-[440px]">
          <span aria-hidden="true" className="inline-flex rounded-xl bg-white/10 p-3 text-[#b9d7e7]"><LockKeyhole className="size-5" /></span>
          <p className="mt-6 text-xs font-semibold uppercase tracking-[0.16em] text-[#b9d7e7]">Acesso à plataforma</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.025em]">Bem-vindo de volta</h1>
          <p className="mt-2 text-sm leading-6 text-[#d8e7f0]">Entre com a senha de acesso para gerenciar as licenças da organização.</p>
          <form className="mt-8" onSubmit={(event) => { event.preventDefault(); login.mutate() }}>
            <label htmlFor="senha-acesso" className="mb-2 block text-sm font-semibold">Senha de acesso</label>
            <div className="relative">
              <Input id="senha-acesso" name="password" type={mostrar ? 'text' : 'password'} value={senha} onChange={(event) => setSenha(event.target.value)} className="h-12 border-white/30 bg-white pr-12 text-[#172334] placeholder:text-[#64748b] focus-visible:border-[#8fbbd5] focus-visible:ring-[#8fbbd5]/35" placeholder="Digite sua senha…" autoComplete="current-password" required aria-invalid={!!erro} aria-describedby={erro ? 'erro-login' : undefined} />
              <button type="button" className="absolute right-1.5 top-1.5 rounded-lg p-2.5 text-[#64748b] hover:bg-[#eaf3f9] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#8fbbd5]" onClick={() => setMostrar(!mostrar)} aria-label={mostrar ? 'Ocultar senha' : 'Mostrar senha'}>{mostrar ? <EyeOff aria-hidden="true" className="size-4" /> : <Eye aria-hidden="true" className="size-4" />}</button>
            </div>
            {erro && <div id="erro-login" role="alert" aria-live="polite" className="mt-3 rounded-xl border border-red-300/60 bg-red-50 px-3.5 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">{erro.message}{erro.status === 401 && typeof (erro as any).tentativas_restantes === 'number' ? ` Restam ${(erro as any).tentativas_restantes} tentativas.` : ''}</div>}
            <Button type="submit" variant="primary" className="mt-5 h-12 w-full bg-white text-[#102c50] hover:bg-[#eaf3f9]" disabled={login.isPending} aria-busy={login.isPending}>{login.isPending ? 'Verificando…' : <>Acessar plataforma <ArrowRight aria-hidden="true" className="size-4" /></>}</Button>
          </form>
          <div className="mt-7 flex items-center justify-center gap-2 text-xs text-[#b9cddd]"><ShieldCheck aria-hidden="true" className="size-4 text-[#8fbbd5]" />Conexão segura · acesso restrito</div>
        </div>
      </section>
    </main>
  )
}
