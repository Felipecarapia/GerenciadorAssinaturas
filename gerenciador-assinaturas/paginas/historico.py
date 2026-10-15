"""Histórico geral com filtro por período (RF-22 a RF-24)."""
from datetime import timedelta

import pandas as pd
import streamlit as st

from componentes import dialogos
from componentes.ui import base, baixar_excel, cabecalho
from servicos import calculos as calc
from servicos.cadastros import hoje
from servicos.esquema import EVENTOS

cabecalho("Histórico", "Toda alteração feita pelo app ou direto na planilha")

b = base()
hist = b.historico.copy()

if hist.empty:
    st.info("Nenhuma alteração registrada ainda. As alterações aparecem aqui assim que acontecem.",
            icon=":material/history:")
    st.stop()

hist["_quando"] = pd.to_datetime(hist["Data e hora"].map(calc.para_datahora), errors="coerce")
hist = hist.sort_values("_quando", ascending=False)

with st.container(border=True):
    f1, f2, f3, f4 = st.columns([1.6, 1.6, 1, 1.6])
    atalhos = {"Últimos 7 dias": 7, "Últimos 30 dias": 30, "Últimos 90 dias": 90,
               "Últimos 12 meses": 365, "Tudo": None, "Escolher datas": "custom"}
    atalho = f1.selectbox("Período", list(atalhos), index=1, key="hist_periodo")
    if atalhos[atalho] == "custom":
        intervalo = f1.date_input("De / até", value=(hoje() - timedelta(days=30), hoje()),
                                  format="DD/MM/YYYY", key="hist_datas")
        inicio, fim = (intervalo if isinstance(intervalo, tuple) and len(intervalo) == 2
                       else (intervalo[0], intervalo[0]) if isinstance(intervalo, tuple) else (intervalo, intervalo))
    elif atalhos[atalho] is None:
        inicio, fim = None, None
    else:
        inicio, fim = hoje() - timedelta(days=atalhos[atalho]), hoje()
    eventos = f2.multiselect("Evento", EVENTOS, placeholder="Todos", key="hist_eventos")
    origem = f3.selectbox("Origem", ["Todas", "app", "planilha"], key="hist_origem")
    assin = f4.selectbox("Assinatura", ["Todas"] + sorted(hist["Assinatura"].astype(str).unique()),
                         key="hist_assin")

f = hist
if inicio is not None:
    f = f[(f["_quando"].dt.date >= inicio) & (f["_quando"].dt.date <= fim)]
if eventos:
    f = f[f["Evento"].isin(eventos)]
if origem != "Todas":
    f = f[f["Origem"].astype(str).str.lower() == origem]
if assin != "Todas":
    f = f[f["Assinatura"].astype(str) == assin]

m1, m2, m3 = st.columns(3)
m1.metric("Registros no período", len(f))
m2.metric("Pelo app", int((f["Origem"].astype(str).str.lower() == "app").sum()))
m3.metric("Direto na planilha", int((f["Origem"].astype(str).str.lower() == "planilha").sum()))

aba_tabela, aba_tempo = st.tabs([":material/table: Tabela", ":material/timeline: Linha do tempo"])
with aba_tabela:
    tabela = pd.DataFrame({
        "Data e hora": f["_quando"], "Origem": f["Origem"], "Quem": f["Quem"],
        "Assinatura": f["Assinatura"], "Evento": f["Evento"],
        "Detalhe": [dialogos.descrever(r) for _, r in f.iterrows()],
        "Campo": f["Campo"], "Valor anterior": f["Valor anterior"], "Valor novo": f["Valor novo"],
    })
    st.dataframe(tabela, hide_index=True, width="stretch", column_config={
        "Data e hora": st.column_config.DatetimeColumn("Data e hora", format="DD/MM/YYYY HH:mm"),
        "Detalhe": st.column_config.TextColumn("Detalhe", width="medium"),
    })
    baixar_excel(tabela.assign(**{"Data e hora": tabela["Data e hora"].dt.strftime("%d/%m/%Y %H:%M")}),
                 "historico", "Histórico")
with aba_tempo:
    if f.empty:
        st.info("Nada no período escolhido.")
    else:
        limite = 200
        st.caption(f"Mostrando os {min(limite, len(f))} registros mais recentes do filtro.")
        st.html(dialogos.linha_do_tempo_html(f.head(limite), mostrar_assinatura=True))
