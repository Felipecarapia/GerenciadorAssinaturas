"""Dashboard: 5 cards, 4 gráficos e alertas de vencimento (RF-05 a RF-09)."""
import pandas as pd
import streamlit as st

from componentes import dialogos
from componentes.ui import base, cabecalho, estado_vazio, reais
from servicos import calculos as calc
from servicos import graficos
from servicos.cadastros import agora

dialogos.mostrar_aviso_pendente()
cabecalho("Dashboard", "Quanto a empresa gasta com software, quem usa e o que vence em breve")

b = base()
df = b.assinaturas

if df.empty:
    estado_vazio("Ainda não há assinaturas cadastradas")
    st.stop()

ind = calc.indicadores(df, b.funcionarios)
evolucao = calc.evolucao_12_meses(df, b.historico, agora())

# ---------- 5 cards (RF-05) ----------
c = st.columns(5)
c[0].metric("Assinaturas ativas", ind["total_ativas"], help="Status = Ativa")
c[1].metric("Gasto mensal", reais(ind["gasto_mensal"]),
            help="Só ativas. Anual ÷ 12, trimestral ÷ 3, semestral ÷ 6. Vitalício não entra.",
            chart_data=evolucao["Gasto mensal"].tolist(), chart_type="area")
c[2].metric("Gasto anual", reais(ind["gasto_anual"]), help="Gasto mensal × 12")
c[3].metric("Vencendo em 30 dias", ind["vencendo_30"],
            delta=f"{ind['vencidas']} vencida(s)" if ind["vencidas"] else "nenhuma vencida",
            delta_color="inverse" if ind["vencidas"] else "off", delta_arrow="off")
c[4].metric("Colaboradores", ind["colaboradores"])

# ---------- 4 gráficos em grade 2 × 2 (RF-07) ----------
cfg = {"displayModeBar": False, "locale": "pt-BR"}
g1, g2 = st.columns(2)
with g1.container(border=True):
    st.markdown("**Gasto mensal por categoria**")
    st.plotly_chart(graficos.donut_categoria(calc.gasto_por_categoria(df)), config=cfg, key="g_cat")
with g2.container(border=True):
    st.markdown("**Assinaturas por status**")
    st.plotly_chart(graficos.barras_status(calc.contagem_por_status(df, b.listas["Status"])), config=cfg,
                    key="g_status")
g3, g4 = st.columns(2)
with g3.container(border=True):
    st.markdown("**Evolução do gasto mensal — 12 meses**")
    st.plotly_chart(graficos.linha_evolucao(evolucao), config=cfg, key="g_evol")
with g4.container(border=True):
    st.markdown("**Top 5 mais caras (custo mensal)**")
    st.plotly_chart(graficos.barras_top5(calc.top_mais_caras(df)), config=cfg, key="g_top")

# ---------- alertas de vencimento (RF-08) ----------
st.markdown("### :material/notifications_active: Alertas de vencimento")
al = calc.alertas(df)
if al.empty:
    st.info("Nenhuma assinatura com data de vencimento.")
else:
    cont = al["nivel"].value_counts()
    opcoes = {
        f"🔴 Urgente ({cont.get('vermelho', 0)})": ["vermelho"],
        f"🟡 Atenção ({cont.get('amarelo', 0)})": ["amarelo"],
        f"🟢 Em dia ({cont.get('verde', 0)})": ["verde"],
        "Todos": ["vermelho", "amarelo", "verde"],
    }
    escolha = st.segmented_control("Urgência", list(opcoes), default=list(opcoes)[0], key="dash_urg",
                                   label_visibility="collapsed")
    niveis = opcoes.get(escolha or "Todos", opcoes["Todos"])
    st.caption("🔴 vencida ou até 7 dias · 🟡 de 8 a 30 dias · 🟢 acima de 30 dias")
    mostrar = al[al["nivel"].isin(niveis)]
    if mostrar.empty:
        st.success("Nada nesta faixa.", icon=":material/check:")
    else:
        st.dataframe(
            pd.DataFrame({
                "": mostrar["alerta"], "Assinatura": mostrar["Nome"], "Situação": mostrar["texto_alerta"],
                "Vencimento": pd.to_datetime(mostrar["venc_data"]), "Plano": mostrar["Plano"],
                "Valor (R$)": mostrar["valor_num"], "Status": mostrar["Status"],
            }),
            hide_index=True, width="stretch",
            column_config={
                "": st.column_config.TextColumn("", width=40),
                "Vencimento": st.column_config.DateColumn(format="DD/MM/YYYY"),
                "Valor (R$)": st.column_config.NumberColumn("Valor", format="localized"),
            },
        )
