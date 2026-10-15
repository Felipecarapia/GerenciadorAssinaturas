"""Peças de interface reutilizáveis: cabeçalho, dados carregados, erros, downloads."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from servicos import calculos as calc
from servicos import planilha
from servicos.cadastros import agora
from servicos.esquema import ABA_ASSINATURAS, ABA_FUNCIONARIOS, ABA_HISTORICO

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
    return Base(calc.preparar_assinaturas(ass, agora().date()), func, hist, planilha.listas())


def atualizar():
    """RF-09: busca na hora o que foi editado na planilha."""
    planilha.limpar_cache()
    st.toast("Dados atualizados com a planilha.", icon=":material/sync:")


def cabecalho(titulo: str, subtitulo: str = "", botao_atualizar: bool = True):
    col1, col2 = st.columns([5, 1], vertical_alignment="bottom")
    with col1:
        st.markdown(f"<div class='ga-titulo'>\n\n# {titulo}\n\n</div>", unsafe_allow_html=True)
        if subtitulo:
            st.markdown(f"<div class='ga-sub'>{subtitulo}</div>", unsafe_allow_html=True)
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
