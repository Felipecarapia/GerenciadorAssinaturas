"""Gerenciador de Assinaturas — ponto de entrada e navegação lateral."""
import streamlit as st

from componentes import login
from componentes.ui import RAIZ, carregar_css
from servicos import planilha

st.set_page_config(
    page_title="Licenzy | Gestão de Assinaturas",
    page_icon=str(RAIZ / "assets" / "icone.svg"),
    layout="wide",
    initial_sidebar_state="expanded",
)
carregar_css()

# RF-01: nenhuma página carrega sem a senha correta
if not login.autenticado():
    login.tela()
    st.stop()

st.logo(str(RAIZ / "assets" / "logo_licenzy.png"),
        icon_image=str(RAIZ / "assets" / "icone.svg"), size="large")


def _rotulo_pendencias() -> str:
    try:
        from componentes.ui import base
        from servicos import pendencias

        b = base()
        qtd = len(pendencias.listar(planilha.ler("Assinaturas"), b.funcionarios, b.listas))
        return f"Pendências ({qtd})" if qtd else "Pendências"
    except Exception:
        return "Pendências"


paginas_gestao = [
    st.Page("paginas/dashboard.py", title="Dashboard", icon=":material/space_dashboard:", default=True),
    st.Page("paginas/assinaturas.py", title="Assinaturas", icon=":material/subscriptions:"),
    st.Page("paginas/pessoas.py", title="Pessoas", icon=":material/group:"),
    st.Page("paginas/projetos.py", title="Projetos", icon=":material/folder_managed:"),
]
paginas_analise = [
    st.Page("paginas/relatorios.py", title="Relatórios", icon=":material/description:"),
    st.Page("paginas/historico.py", title="Histórico", icon=":material/history:"),
    st.Page("paginas/pendencias.py", title=_rotulo_pendencias(), icon=":material/report:",
            url_path="pendencias"),
]


def _sair():
    login.sair()
    st.switch_page(paginas_gestao[0])  # volta para o início, que mostra o login


pagina_sair = st.Page(_sair, title="Sair", icon=":material/logout:", url_path="sair")

pagina = st.navigation(
    {"Gestão": paginas_gestao, "Análise e controle": paginas_analise, "Conta": [pagina_sair]},
    position="sidebar",
)
with st.sidebar:
    st.markdown(
        "<div class='ga-sidebar-meta'><span class='ga-sidebar-dot'></span>"
        "Sistema conectado<br><strong>Ambiente de gestão corporativa</strong></div>",
        unsafe_allow_html=True,
    )

try:
    pagina.run()
except planilha.ErroPlanilha as erro:
    st.error(str(erro), icon=":material/cloud_off:")
    if st.button("Tentar de novo", icon=":material/refresh:"):
        planilha.limpar_cache()
        st.rerun()
