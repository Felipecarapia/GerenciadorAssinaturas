import { createRootRoute, createRoute, createRouter, lazyRouteComponent, Outlet, redirect } from '@tanstack/react-router'
import { AppShell } from './components/AppShell'
import { LoginPage } from './routes/Login'

const DashboardPage = lazyRouteComponent(() => import('./routes/Dashboard'), 'DashboardPage')
const AssinaturasPage = lazyRouteComponent(() => import('./routes/Assinaturas'), 'AssinaturasPage')
const PessoasPage = lazyRouteComponent(() => import('./routes/Pessoas'), 'PessoasPage')
const ProjetosPage = lazyRouteComponent(() => import('./routes/Projetos'), 'ProjetosPage')
const RelatoriosPage = lazyRouteComponent(() => import('./routes/Relatorios'), 'RelatoriosPage')
const HistoricoPage = lazyRouteComponent(() => import('./routes/Historico'), 'HistoricoPage')
const PendenciasPage = lazyRouteComponent(() => import('./routes/Pendencias'), 'PendenciasPage')

const rootRoute = createRootRoute({ component: () => <Outlet /> })
const loginRoute = createRoute({ getParentRoute: () => rootRoute, path: '/login', component: LoginPage })
const appRoute = createRoute({ getParentRoute: () => rootRoute, id: 'app', component: AppShell })

const indexRoute = createRoute({ getParentRoute: () => appRoute, path: '/', beforeLoad: () => { throw redirect({ to: '/assinaturas', replace: true }) } })
const dashboardRoute = createRoute({ getParentRoute: () => appRoute, path: '/dashboard', component: DashboardPage })
const assinaturasRoute = createRoute({ getParentRoute: () => appRoute, path: '/assinaturas', component: AssinaturasPage })
const pessoasRoute = createRoute({ getParentRoute: () => appRoute, path: '/pessoas', component: PessoasPage })
const projetosRoute = createRoute({ getParentRoute: () => appRoute, path: '/projetos', component: ProjetosPage })
const relatoriosRoute = createRoute({ getParentRoute: () => appRoute, path: '/relatorios', component: RelatoriosPage })
const historicoRoute = createRoute({ getParentRoute: () => appRoute, path: '/historico', component: HistoricoPage })
const pendenciasRoute = createRoute({ getParentRoute: () => appRoute, path: '/pendencias', component: PendenciasPage })

const routeTree = rootRoute.addChildren([
  loginRoute,
  appRoute.addChildren([indexRoute, dashboardRoute, assinaturasRoute, pessoasRoute, projetosRoute, relatoriosRoute, historicoRoute, pendenciasRoute]),
])

export const router = createRouter({ routeTree, defaultPreload: 'intent' })

declare module '@tanstack/react-router' {
  interface Register { router: typeof router }
}
