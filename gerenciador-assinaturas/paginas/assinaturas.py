"""Assinaturas: tabela, filtros, cadastro, edição e exclusão (RF-10 a RF-16)."""
import pandas as pd
import streamlit as st

from componentes import dialogos
from componentes.ui import base, baixar_excel, cabecalho, dataframe_limitado, estado_vazio, reais
from servicos import calculos as calc

dialogos.mostrar_aviso_pendente()
cabecalho("Assinaturas", "Todas as ferramentas contratadas, com valor, vencimento e quem usa")

b = base()
df = b.assinaturas
usuarios = calc.usuarios_por_assinatura(b.funcionarios)
projetos = calc.projetos_por_assinatura(b.projetos, b.usos_projeto)

if df.empty:
    estado_vazio("Nenhuma assinatura cadastrada ainda")
    if st.button("Nova assinatura", type="primary", icon=":material/add:"):
        dialogos.abrir_assinatura()
    st.stop()

# ---------- contadores ----------
ind = calc.indicadores(df, b.funcionarios)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Cadastradas", len(df))
c2.metric("Ativas", ind["total_ativas"])
c3.metric("Gasto mensal", reais(ind["gasto_mensal"]))
c4.metric("Vencem em 30 dias", ind["vencendo_30"],
          delta=f"{ind['vencidas']} vencida(s)" if ind["vencidas"] else None,
          delta_color="inverse", delta_arrow="off")

# ---------- filtros (RF-11) ----------
with st.container(border=True):
    f1, f2, f3, f4 = st.columns([2, 1.4, 1.4, 1.2])
    busca = f1.text_input("Buscar por nome", placeholder="Digite parte do nome",
                          icon=":material/search:", key="ass_busca")
    status = f2.multiselect("Status", b.listas["Status"], key="ass_status", placeholder="Todos")
    cats = f3.multiselect("Categoria", sorted(set(b.listas["Categorias"]) | set(df["Categoria"].astype(str)) - {""}),
                          key="ass_cat", placeholder="Todas")
    prazos = {"Todos": None, "Vencidas": -1, "Até 7 dias": 7, "Até 30 dias": 30,
              "Até 60 dias": 60, "Até 90 dias": 90}
    prazo = f4.selectbox("Vencimento", list(prazos), key="ass_prazo")

filtrado = df.copy()
if busca:
    filtrado = filtrado[filtrado["Nome"].astype(str).map(calc.normalizar).str.contains(calc.normalizar(busca), regex=False)]
if status:
    filtrado = filtrado[filtrado["Status"].isin(status)]
if cats:
    filtrado = filtrado[filtrado["Categoria"].isin(cats)]
if prazos[prazo] is not None:
    d = filtrado["dias"]
    if prazos[prazo] < 0:
        filtrado = filtrado[d.notna() & (d.fillna(0).astype(int) < 0)]
    else:
        filtrado = filtrado[d.notna() & (d.fillna(10**6).astype(int) <= prazos[prazo])]

# ---------- tabela (RF-10) ----------
tabela = pd.DataFrame({
    "Logo": filtrado["Logo (URL)"].replace("", None),
    "Nome": filtrado["Nome"],
    "Categoria": filtrado["Categoria"],
    "Plano": filtrado["Plano"],
    "Valor (R$)": filtrado["valor_num"],
    "Mensal (R$)": filtrado["mensal"].round(2),
    "Vencimento": pd.to_datetime(filtrado["venc_data"], errors="coerce"),
    "Status": filtrado["Status"],
    "Alerta": (filtrado["alerta"] + " " + filtrado["texto_alerta"]),
    "Usuários": filtrado["Nome"].map(lambda n: len(usuarios.get(str(n), []))),
    "Projetos": filtrado["ID"].astype(str).map(lambda i: projetos.get(i, [])),
}).reset_index(drop=True)
ids = filtrado["ID"].astype(str).tolist()

b1, b2, b3, b4, b5, _ = st.columns([1.3, 0.9, 0.9, 1.4, 1.0, 2.5])
st.caption(f"{len(tabela)} de {len(df)} assinatura(s). Clique numa linha para editar, excluir, marcar como pago ou ver o histórico. "
           "Clique no título de uma coluna para ordenar.")
selecao, tabela_visivel = dataframe_limitado(
    tabela, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
    key="tabela_assinaturas", row_height=40,
    column_config={
        "Logo": st.column_config.ImageColumn("", width=48),
        "Nome": st.column_config.TextColumn("Nome", width="medium"),
        "Valor (R$)": st.column_config.NumberColumn("Valor", format="localized", help="Valor cobrado por período do plano"),
        "Mensal (R$)": st.column_config.NumberColumn("Custo mensal", format="localized",
                                                     help="Só ativas. Anual ÷ 12; vitalício não entra."),
        "Vencimento": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
        "Alerta": st.column_config.TextColumn("Alerta", width="medium"),
        "Usuários": st.column_config.NumberColumn("Usuários", width="small"),
        "Projetos": st.column_config.ListColumn("Usada nos projetos", width="large"),
    },
)
linhas = selecao.selection.rows if selecao else []
ids_visiveis = ids[:len(tabela_visivel)]
sel = ids_visiveis[linhas[0]] if linhas else None
nome_sel = str(tabela_visivel.iloc[linhas[0]]["Nome"]) if linhas else ""
plano_sel = str(tabela_visivel.iloc[linhas[0]]["Plano"]) if linhas else ""
venc_sel = tabela_visivel.iloc[linhas[0]]["Vencimento"] if linhas else None

pode_pagar = (
    sel is not None
    and calc.normalizar(plano_sel) in ("mensal", "anual")
    and pd.notna(venc_sel)
    and calc.para_data(venc_sel) is not None
)

if b1.button("Nova assinatura", type="primary", icon=":material/add:", width="stretch"):
    dialogos.abrir_assinatura()
if b2.button("Editar", icon=":material/edit:", disabled=sel is None, width="stretch"):
    dialogos.abrir_assinatura(sel)
if b3.button("Excluir", icon=":material/delete:", disabled=sel is None, width="stretch"):
    dialogos.confirmar_exclusao_assinatura(sel, nome_sel, len(usuarios.get(nome_sel, [])))
if b4.button("Marcar como pago", icon=":material/payments:", disabled=not pode_pagar, width="stretch",
             help="Avança o próximo vencimento e registra no Histórico"):
    dialogos.confirmar_pagamento_assinatura(sel)
if b5.button("Histórico", icon=":material/history:", disabled=sel is None, width="stretch"):
    dialogos.abrir_linha_do_tempo(nome_sel)

exportar = tabela.drop(columns=["Logo"]).assign(
    Vencimento=tabela["Vencimento"].dt.date,
    Alerta=filtrado["texto_alerta"].values,
    Projetos=tabela["Projetos"].map(lambda itens: ", ".join(itens)),
)
baixar_excel(exportar, "assinaturas", "Assinaturas", moedas=("Valor (R$)", "Mensal (R$)"), datas=("Vencimento",))
