"""Relatórios para baixar em PDF e Excel (RF-27 a RF-30). Cada um tem prévia na tela."""
import pandas as pd
import streamlit as st

from componentes.ui import base, cabecalho, estado_vazio, reais
from servicos import calculos as calc
from servicos import relatorios as rel
from servicos.cadastros import agora

cabecalho("Relatórios", "Prévia na tela e download em PDF ou Excel")

b = base()
if b.assinaturas.empty:
    estado_vazio("Sem dados para gerar relatórios")
    st.stop()

momento = agora()
dados = rel.Dados(b.assinaturas, b.funcionarios, b.historico, momento)
sufixo = f"{momento:%Y-%m-%d}"
PDF, XLSX = "application/pdf", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

abas = st.tabs([
    ":material/summarize: Resumo Geral",
    ":material/category: Por Categoria",
    ":material/event_upcoming: A Vencer",
    ":material/groups: Colaboradores e Departamentos",
])

# ---------- RF-27 ----------
with abas[0]:
    st.markdown("Assinaturas, gastos e colaboradores num só documento, com os gráficos do dashboard.")
    ind = calc.indicadores(b.assinaturas, b.funcionarios)
    c = st.columns(4)
    c[0].metric("Ativas", ind["total_ativas"])
    c[1].metric("Gasto mensal", reais(ind["gasto_mensal"]))
    c[2].metric("Gasto anual", reais(ind["gasto_anual"]))
    c[3].metric("Colaboradores", ind["colaboradores"])
    st.dataframe(calc.gasto_por_categoria(b.assinaturas), hide_index=True, width="stretch",
                 column_config={"Gasto mensal": st.column_config.NumberColumn("Gasto mensal (R$)", format="localized")})
    st.download_button("Baixar PDF", data=lambda: rel.resumo_geral_pdf(dados),
                       file_name=f"resumo_geral_{sufixo}.pdf", mime=PDF, type="primary",
                       icon=":material/picture_as_pdf:", on_click="ignore", key="dl_resumo")

# ---------- RF-28 ----------
with abas[1]:
    st.markdown("Planilha Excel com uma aba de resumo e **uma aba por categoria**.")
    df = b.assinaturas.assign(Categoria=b.assinaturas["Categoria"].replace("", "Sem categoria"))
    previa = df.groupby("Categoria", as_index=False).agg(
        Assinaturas=("ID", "count"), Ativas=("Status", lambda s: int((s == "Ativa").sum())),
        **{"Gasto mensal": ("mensal", "sum")}).round(2).sort_values("Gasto mensal", ascending=False)
    st.dataframe(previa, hide_index=True, width="stretch",
                 column_config={"Gasto mensal": st.column_config.NumberColumn("Gasto mensal (R$)", format="localized")})
    st.download_button("Baixar Excel", data=lambda: rel.por_categoria_xlsx(dados),
                       file_name=f"assinaturas_por_categoria_{sufixo}.xlsx", mime=XLSX, type="primary",
                       icon=":material/table_view:", on_click="ignore", key="dl_cat")

# ---------- RF-29 ----------
with abas[2]:
    dias = st.segmented_control("Período", [30, 60, 90], default=30, format_func=lambda d: f"{d} dias",
                                key="rel_dias") or 30
    st.markdown(f"Assinaturas que vencem nos próximos **{dias} dias**, incluindo as já vencidas.")
    av = calc.a_vencer(b.assinaturas, dias)
    if av.empty:
        st.success("Nenhuma assinatura vence nesse período.", icon=":material/check:")
    else:
        st.dataframe(pd.DataFrame({
            "": av["alerta"], "Assinatura": av["Nome"], "Situação": av["texto_alerta"],
            "Vencimento": pd.to_datetime(av["venc_data"]), "Plano": av["Plano"], "Valor (R$)": av["valor_num"],
        }), hide_index=True, width="stretch", column_config={
            "": st.column_config.TextColumn("", width=40),
            "Vencimento": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Valor (R$)": st.column_config.NumberColumn("Valor", format="localized"),
        })
    st.download_button("Baixar PDF", data=lambda: rel.a_vencer_pdf(dados, dias),
                       file_name=f"a_vencer_{dias}_dias_{sufixo}.pdf", mime=PDF, type="primary",
                       icon=":material/picture_as_pdf:", on_click="ignore", key=f"dl_venc_{dias}")

# ---------- RF-30 ----------
with abas[3]:
    st.markdown("Quem usa cada assinatura e quanto cada departamento representa. "
                "O custo de cada assinatura é dividido entre os seus usuários.")
    p1, p2 = st.columns([1, 1.4])
    with p1:
        st.markdown("**Gastos por departamento**")
        st.dataframe(calc.gasto_por_departamento(b.assinaturas, b.funcionarios), hide_index=True, width="stretch",
                     column_config={
                         "Gasto mensal": st.column_config.NumberColumn("Mensal (R$)", format="localized"),
                         "Gasto anual": st.column_config.NumberColumn("Anual (R$)", format="localized")})
    with p2:
        st.markdown("**Colaboradores por assinatura**")
        cpa = calc.colaboradores_por_assinatura(b.assinaturas, b.funcionarios)
        st.dataframe(cpa[["Assinatura", "Qtd. usuários", "Usuários", "Custo por usuário"]], hide_index=True,
                     width="stretch", column_config={
                         "Custo por usuário": st.column_config.NumberColumn("Por usuário (R$)", format="localized")})
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("Baixar Excel", data=lambda: rel.colaboradores_xlsx(dados),
                       file_name=f"colaboradores_e_departamentos_{sufixo}.xlsx", mime=XLSX, type="primary",
                       icon=":material/table_view:", on_click="ignore", key="dl_col_x", width="stretch")
    d2.download_button("Baixar PDF", data=lambda: rel.colaboradores_pdf(dados),
                       file_name=f"colaboradores_e_departamentos_{sufixo}.pdf", mime=PDF,
                       icon=":material/picture_as_pdf:", on_click="ignore", key="dl_col_p", width="stretch")
