"""Pessoas: colaboradores, vínculos e custo por pessoa (RF-17 a RF-21)."""
import pandas as pd
import streamlit as st

from componentes import dialogos
from componentes.ui import base, baixar_excel, cabecalho, dataframe_limitado, estado_vazio, reais
from servicos import calculos as calc

dialogos.mostrar_aviso_pendente()
cabecalho("Pessoas", "Colaboradores e as assinaturas que cada um usa")

b = base()
func = b.funcionarios

if func.empty:
    estado_vazio("Nenhuma pessoa cadastrada ainda")
    if st.button("Nova pessoa", type="primary", icon=":material/person_add:"):
        dialogos.abrir_pessoa()
    st.stop()

custos = calc.custo_por_pessoa(b.assinaturas, func)

c1, c2, c3 = st.columns(3)
c1.metric("Colaboradores", len(func))
c2.metric("Departamentos", custos["Departamento"].nunique())
media = custos["Custo mensal"].mean() if len(custos) else 0
c3.metric("Custo mensal médio por pessoa", reais(media))

with st.container(border=True):
    f1, f2 = st.columns([2, 1.5])
    busca = f1.text_input("Buscar por nome, e-mail ou departamento", icon=":material/search:",
                          placeholder="Digite para filtrar", key="pes_busca")
    deps = f2.multiselect("Departamento", sorted(custos["Departamento"].unique()), placeholder="Todos",
                          key="pes_deps")

filtrado = custos.merge(func[["ID", "Assinaturas"]], on="ID", how="left")
if busca:
    alvo = calc.normalizar(busca)
    texto = (filtrado["Nome completo"].astype(str) + " " + filtrado["E-mail"].astype(str) + " "
             + filtrado["Departamento"].astype(str)).map(calc.normalizar)
    filtrado = filtrado[texto.str.contains(alvo, regex=False)]
if deps:
    filtrado = filtrado[filtrado["Departamento"].isin(deps)]
filtrado = filtrado.sort_values("Nome completo").reset_index(drop=True)

b1, b2, b3, _ = st.columns([1.3, 1, 1, 4])
st.caption(f"{len(filtrado)} de {len(func)} pessoa(s). Clique numa linha para ver o detalhe, editar ou excluir.")
selecao, pessoas_visiveis = dataframe_limitado(
    filtrado[["Nome completo", "E-mail", "Departamento", "Cargo", "Assinaturas", "Custo mensal"]]
    .assign(Assinaturas=filtrado["Assinaturas"].map(calc.separar_lista)),
    hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row", key="tabela_pessoas",
    column_config={
        "E-mail": st.column_config.TextColumn("E-mail", width="medium"),
        "Assinaturas": st.column_config.ListColumn("Assinaturas", width="large"),
        "Custo mensal": st.column_config.NumberColumn("Custo mensal (R$)", format="localized",
                                                      help="Cada assinatura dividida entre os seus usuários"),
    },
)
linhas = selecao.selection.rows if selecao else []
sel = filtrado.iloc[linhas[0]] if linhas and linhas[0] < len(pessoas_visiveis) else None

if b1.button("Nova pessoa", type="primary", icon=":material/person_add:", width="stretch"):
    dialogos.abrir_pessoa()
if b2.button("Editar", icon=":material/edit:", disabled=sel is None, width="stretch"):
    dialogos.abrir_pessoa(str(sel["ID"]))
if b3.button("Excluir", icon=":material/delete:", disabled=sel is None, width="stretch"):
    dialogos.confirmar_exclusao_pessoa(str(sel["ID"]), str(sel["Nome completo"]))

# ---------- detalhe da pessoa (RF-20) ----------
if sel is not None:
    with st.container(border=True):
        st.markdown(f"#### :material/person: {sel['Nome completo']}")
        st.caption(f"{sel['E-mail']} · {sel['Departamento']}{' · ' + str(sel['Cargo']) if str(sel['Cargo']).strip() else ''}")
        det = calc.detalhe_pessoa(b.assinaturas, func, str(sel["ID"]))
        d1, d2 = st.columns([1, 3])
        d1.metric("Custo mensal que representa", reais(float(det["Parte da pessoa"].sum()) if not det.empty else 0))
        d1.metric("Assinaturas", len(det))
        if det.empty:
            d2.info("Esta pessoa não usa nenhuma assinatura.")
        else:
            with d2:
                dataframe_limitado(det, key=f"detalhe_pessoa_{sel['ID']}", hide_index=True, width="stretch", column_config={
                "Custo mensal total": st.column_config.NumberColumn("Custo mensal total (R$)", format="localized"),
                "Parte da pessoa": st.column_config.NumberColumn("Parte da pessoa (R$)", format="localized"),
                })

baixar_excel(filtrado.drop(columns=["ID"]), "pessoas", "Pessoas", moedas=("Custo mensal",))
