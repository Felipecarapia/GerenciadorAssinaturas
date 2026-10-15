"""Pendências: dados inconsistentes da planilha (RF-25 e RF-26)."""
import streamlit as st

from componentes import dialogos
from componentes.ui import base, cabecalho
from servicos import cadastros, pendencias, planilha
from servicos.esquema import ABA_ASSINATURAS

dialogos.mostrar_aviso_pendente()
cabecalho("Pendências", "Problemas nos dados da planilha que precisam de correção")

b = base()
bruto = planilha.ler(ABA_ASSINATURAS)  # sem conversões, para ver o que está digitado
lista = pendencias.listar(bruto, b.funcionarios, b.listas)

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

nomes_validos = set(b.nomes_assinaturas)
for i, p in lista.reset_index(drop=True).iterrows():
    with st.container(border=True):
        c1, c2 = st.columns([4, 1.4], vertical_alignment="center")
        with c1:
            st.markdown(f"**{p['Tipo']}** · {p['Item']}")
            st.caption(f":material/table_rows: Aba **{p['Aba']}**, linha **{p['Linha']}** — {p['Descrição']}")
        with c2:
            if p["Tipo"] == pendencias.T_INEXISTENTE:
                if st.button("Remover escolhas inválidas", key=f"pend_rm_{i}", icon=":material/link_off:",
                             width="stretch"):
                    removidas = cadastros.remover_escolhas_invalidas(p["ID"], nomes_validos)
                    dialogos.avisar_depois(f"Removido de {p['Item']}: {', '.join(removidas) or 'nada'}")
                    st.rerun()
            if st.button("Corrigir no app", key=f"pend_fix_{i}", icon=":material/build:", width="stretch",
                         type="primary"):
                if p["Aba"] == ABA_ASSINATURAS:
                    dialogos.abrir_assinatura(p["ID"])
                else:
                    dialogos.abrir_pessoa(p["ID"])
