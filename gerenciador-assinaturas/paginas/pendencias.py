"""Pendências: dados inconsistentes da planilha (RF-25 e RF-26)."""
import streamlit as st

from componentes import dialogos
from componentes.ui import base, cabecalho
from servicos import pendencias, planilha, projetos
from servicos.esquema import ABA_ASSINATURAS, ABA_EQUIPE

dialogos.mostrar_aviso_pendente()
cabecalho("Pendências", "Problemas nos dados da planilha que precisam de correção")

b = base()
bruto = planilha.ler(ABA_ASSINATURAS)  # sem conversões, para ver o que está digitado
lista = pendencias.listar(bruto, b.funcionarios, b.listas, b.projetos, planilha.ler(ABA_EQUIPE))

if lista.empty:
    st.success("Nenhuma pendência. Os dados da planilha estão consistentes.", icon=":material/verified:")
    st.stop()

st.warning(f"{len(lista)} pendência(s) encontrada(s). Corrija pelo app ou direto na planilha "
           "(depois clique em Atualizar).", icon=":material/report:")

with st.expander("Como evitar pendências"):
    st.markdown(
        "- **Renomeie assinaturas pelo app**: ele troca o nome em todos os funcionários. Renomear direto na "
        "planilha deixa escolhas antigas inválidas.\n"
        "- **Não use vírgula no nome** de uma assinatura: a planilha separa as escolhas por vírgula.\n"
        "- **Use as listas suspensas** de Categoria, Plano, Status e Departamento (opções na aba Listas)."
    )

tipos = ["Todos"] + sorted(lista["Tipo"].unique())
tipo = st.segmented_control("Tipo", tipos, default="Todos", key="pend_tipo", label_visibility="collapsed")
if tipo and tipo != "Todos":
    lista = lista[lista["Tipo"] == tipo]

for i, p in lista.reset_index(drop=True).iterrows():
    with st.container(border=True):
        c1, c2 = st.columns([4, 1.4], vertical_alignment="center")
        with c1:
            st.markdown(f"**{p['Tipo']}** · {p['Item']}")
            st.caption(f":material/table_rows: Aba **{p['Aba']}**, linha **{p['Linha']}** — {p['Descrição']}")
        with c2:
            if p["Tipo"] in (pendencias.T_INEXISTENTE, pendencias.T_VINCULO_EDITADO):
                if st.button("Recalcular", key=f"pend_rm_{i}", icon=":material/sync:",
                             width="stretch"):
                    alteradas = projetos.sincronizar_derivados()
                    dialogos.avisar_depois(f"Assinaturas recalculadas a partir das equipes: {alteradas['pessoas']} pessoa(s).")
                    st.rerun()
            if st.button("Corrigir no app", key=f"pend_fix_{i}", icon=":material/build:", width="stretch",
                         type="primary"):
                if p["Aba"] == ABA_ASSINATURAS:
                    dialogos.abrir_assinatura(p["ID"])
                else:
                    dialogos.abrir_pessoa(p["ID"])
