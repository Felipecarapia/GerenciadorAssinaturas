"""Projetos: onde cada assinatura é utilizada e como seu custo é distribuído."""
import pandas as pd
import streamlit as st

from componentes import dialogos
from componentes.ui import base, cabecalho, dataframe_limitado, estado_vazio, reais
from servicos import calculos as calc

dialogos.mostrar_aviso_pendente()
cabecalho("Projetos", "Onde cada assinatura é utilizada e quanto cada projeto representa")
b = base()

if b.assinaturas.empty:
    estado_vazio("Cadastre uma assinatura antes de criar projetos", mostrar_exemplo=False)
    st.stop()

custos = calc.custos_por_projeto(b.assinaturas, b.projetos, b.usos_projeto)
c1, c2, c3 = st.columns(3)
c1.metric("Projetos", len(b.projetos))
c2.metric("Projetos ativos", int((b.projetos["Status"].astype(str) == "Ativo").sum()) if not b.projetos.empty else 0)
c3.metric("Custo mensal alocado", reais(float(custos["Custo mensal"].sum()) if not custos.empty else 0))

if st.button("Novo projeto", type="primary", icon=":material/add:"):
    dialogos.abrir_projeto()

if b.projetos.empty:
    estado_vazio("Nenhum projeto cadastrado", mostrar_exemplo=False)
    st.stop()

busca = st.text_input("Buscar projeto, cliente ou responsável", icon=":material/search:")
dados = b.projetos.merge(custos[["ID", "Assinaturas", "Custo mensal", "Custo anual"]], on="ID", how="left")
if busca:
    alvo = calc.normalizar(busca)
    texto = (dados["Nome"].astype(str) + " " + dados["Cliente"].astype(str) + " "
             + dados["Responsável"].astype(str)).map(calc.normalizar)
    dados = dados[texto.str.contains(alvo, regex=False)]
dados = dados.sort_values(["Status", "Nome"]).reset_index(drop=True)

mostrar = pd.DataFrame({
    "Projeto": dados["Nome"], "Cliente": dados["Cliente"], "Responsável": dados["Responsável"],
    "Departamento": dados["Departamento"], "Status": dados["Status"],
    "Assinaturas": dados["Assinaturas"].fillna(0), "Custo mensal": dados["Custo mensal"].fillna(0),
})
selecao, visivel = dataframe_limitado(
    mostrar, key="tabela_projetos", hide_index=True, width="stretch", on_select="rerun",
    selection_mode="single-row", column_config={
        "Custo mensal": st.column_config.NumberColumn("Custo mensal (R$)", format="localized")
    })
linhas = selecao.selection.rows if selecao else []
selecionado = dados.iloc[linhas[0]] if linhas and linhas[0] < len(visivel) else None

a1, a2, a3, _ = st.columns([1, 1.35, 1, 3.65])
if a1.button("Editar", icon=":material/edit:", disabled=selecionado is None, width="stretch"):
    dialogos.abrir_projeto(str(selecionado["ID"]))
ja_concluido = selecionado is not None and calc.normalizar(selecionado["Status"]) == "concluído"
if a2.button("Concluir", icon=":material/task_alt:", disabled=selecionado is None or ja_concluido,
             width="stretch", help="Retira o projeto da divisão de custos ativos"):
    dialogos.confirmar_conclusao_projeto(selecionado.to_dict())
if a3.button("Excluir", icon=":material/delete:", disabled=selecionado is None, width="stretch"):
    dialogos.confirmar_exclusao_projeto(selecionado.to_dict())

if selecionado is not None:
    pid = str(selecionado["ID"])
    usos = b.usos_projeto[b.usos_projeto["Projeto ID"].astype(str) == pid]
    detalhes = usos.merge(
        b.assinaturas[["ID", "Nome", "Plano", "Status", "mensal"]],
        left_on="Assinatura ID", right_on="ID", how="left", suffixes=(" uso", " assinatura"))
    qtd = (b.usos_projeto[b.usos_projeto["Status"].map(calc.normalizar).isin(("ativo", "ativa"))]
           .groupby(b.usos_projeto["Assinatura ID"].astype(str)).size().to_dict())
    if not detalhes.empty:
        detalhes["Parte do projeto"] = [round(float(m or 0) / max(1, qtd.get(str(i), 1)), 2)
                                         for m, i in zip(detalhes["mensal"], detalhes["Assinatura ID"])]
        st.markdown(f"### Assinaturas de {selecionado['Nome']}")
        dataframe_limitado(
            detalhes[["Nome", "Plano", "Status assinatura", "Parte do projeto"]]
            .rename(columns={"Nome": "Assinatura", "Status assinatura": "Status"}),
            key=f"assinaturas_projeto_{pid}", hide_index=True, width="stretch",
            column_config={"Parte do projeto": st.column_config.NumberColumn("Custo alocado (R$)", format="localized")})
