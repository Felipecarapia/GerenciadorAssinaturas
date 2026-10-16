"""Peças de interface reutilizáveis: cabeçalho, dados carregados, erros, downloads."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from servicos import calculos as calc
from servicos import planilha
from servicos.cadastros import agora
from servicos.esquema import (
    ABA_ASSINATURAS, ABA_FUNCIONARIOS, ABA_HISTORICO, ABA_PROJETOS, ABA_USOS_PROJETO,
)

RAIZ = Path(__file__).resolve().parent.parent


def carregar_css():
    css = (RAIZ / "style.css").read_text(encoding="utf-8")
    st.html(f"<style>{css}</style>")


@dataclass
class Base:
    assinaturas: pd.DataFrame  # preparada (com mensal, dias, alerta...)
    funcionarios: pd.DataFrame
    historico: pd.DataFrame
    listas: dict
    projetos: pd.DataFrame
    usos_projeto: pd.DataFrame

    @property
    def nomes_assinaturas(self) -> list[str]:
        if self.assinaturas.empty:
            return []
        return sorted(str(n) for n in self.assinaturas["Nome"] if str(n).strip())


def base() -> Base:
    """Lê as 4 abas (com cache de 60 s) e já calcula as colunas derivadas."""
    ass = planilha.ler(ABA_ASSINATURAS)
    func = planilha.ler(ABA_FUNCIONARIOS)
    hist = planilha.ler(ABA_HISTORICO)
    projetos = planilha.ler(ABA_PROJETOS)
    usos = planilha.ler(ABA_USOS_PROJETO)
    return Base(calc.preparar_assinaturas(ass, agora().date()), func, hist, planilha.listas(), projetos, usos)


def atualizar():
    """RF-09: busca na hora o que foi editado na planilha."""
    planilha.limpar_cache()
    st.toast("Dados atualizados com a planilha.", icon=":material/sync:")


def cabecalho(titulo: str, subtitulo: str = "", botao_atualizar: bool = True):
    col1, col2 = st.columns([5, 1], vertical_alignment="bottom")
    with col1:
        st.markdown(
            f"<div class='ga-page-head'><div class='ga-eyebrow'>Gestão de assinaturas</div>"
            f"<div class='ga-titulo'><h1>{titulo}</h1></div>"
            f"<div class='ga-sub'>{subtitulo}</div></div>",
            unsafe_allow_html=True,
        )
    if botao_atualizar:
        with col2:
            st.button("Atualizar", icon=":material/refresh:", on_click=atualizar,
                      help="Busca agora o que foi editado direto na planilha",
                      width="stretch", key=f"atualizar_{titulo}")
    if planilha.modo_local():
        st.caption(":orange[:material/science:] Modo local de demonstração: os dados ficam num arquivo "
                   "neste servidor. Configure a conta de serviço nos Secrets para usar o Google Sheets.")


def erro_campo(erros: dict, campo: str):
    """Mostra o erro de validação logo abaixo do campo."""
    if erros and campo in erros:
        st.markdown(f":red[:material/error: {erros[campo]}]")


def baixar_excel(df: pd.DataFrame, nome_arquivo: str, titulo: str, moedas=(), datas=(), key=None):
    from servicos.relatorios import tabela_xlsx

    st.download_button(
        "Baixar Excel", data=lambda: tabela_xlsx(df, titulo, moedas, datas),
        file_name=f"{nome_arquivo}_{agora():%Y-%m-%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon=":material/download:", key=key or f"xlsx_{nome_arquivo}", on_click="ignore",
    )


def reais(v) -> str:
    return calc.formatar_reais(v)


def limitar_itens(df: pd.DataFrame, key: str, passo: int = 5) -> pd.DataFrame:
    """Retorna inicialmente 5 linhas e guarda a expansão desta lista na sessão."""
    chave = f"limite_linhas_{key}"
    limite = max(passo, int(st.session_state.get(chave, passo)))
    st.session_state[chave] = limite
    return df.head(limite)


def controle_ver_mais(total: int, exibidos: int, key: str, passo: int = 5):
    """Mostra controles compactos para expandir ou recolher uma lista."""
    chave = f"limite_linhas_{key}"
    if total <= passo:
        return
    c1, c2, _ = st.columns([1.15, 1.15, 5])
    if exibidos < total:
        qtd = min(passo, total - exibidos)
        if c1.button(f"Ver mais ({qtd})", key=f"ver_mais_{key}", icon=":material/expand_more:"):
            st.session_state[chave] = exibidos + passo
            st.rerun()
    if exibidos > passo:
        if c2.button("Ver menos", key=f"ver_menos_{key}", icon=":material/expand_less:"):
            st.session_state[chave] = passo
            st.rerun()


def dataframe_limitado(df: pd.DataFrame, key: str, passo: int = 5, **kwargs):
    """Exibe um dataframe com no máximo 5 linhas inicialmente e botão Ver mais."""
    visivel = limitar_itens(df, key, passo)
    evento = st.dataframe(visivel, key=key, **kwargs)
    controle_ver_mais(len(df), len(visivel), key, passo)
    return evento, visivel


def estado_vazio(mensagem: str, mostrar_exemplo: bool = True):
    with st.container(border=True):
        st.markdown(f"### :material/inbox: {mensagem}")
        if planilha.modo_local() and mostrar_exemplo:
            st.write("No modo de demonstração você pode carregar 20 assinaturas e 15 pessoas fictícias.")
            if st.button("Carregar dados de exemplo", icon=":material/auto_awesome:", type="primary"):
                from servicos import exemplo
                with st.spinner("Preenchendo a planilha de demonstração..."):
                    exemplo.carregar(agora(), com_pendencias=True)
                st.rerun()
