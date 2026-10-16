"""Janelas (st.dialog) de cadastro, edição, exclusão e linha do tempo."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from componentes.ui import base, controle_ver_mais, erro_campo, limitar_itens
from servicos import cadastros, planilha
from servicos import calculos as calc
from servicos.cadastros import ConflitoEdicao, ErroValidacao
from servicos.esquema import ABA_ASSINATURAS, ABA_FUNCIONARIOS, ABA_PROJETOS

PREFIXO = "dlg_"


def _limpar_estado():
    for k in [k for k in st.session_state if str(k).startswith(PREFIXO)]:
        del st.session_state[k]


def avisar_depois(texto: str, icone=":material/check_circle:"):
    st.session_state["aviso_pendente"] = (texto, icone)


def mostrar_aviso_pendente():
    if "aviso_pendente" in st.session_state:
        texto, icone = st.session_state.pop("aviso_pendente")
        st.toast(texto, icon=icone)


def _indice(opcoes, valor):
    valor = "" if calc.vazio(valor) else str(valor).strip()
    return opcoes.index(valor) if valor in opcoes else None


def _opcoes_com_atual(opcoes: list[str], atual) -> list[str]:
    """Mantém a opção que está na planilha mesmo se ela saiu da aba Listas."""
    atual = "" if calc.vazio(atual) else str(atual).strip()
    return opcoes + ([atual] if atual and atual not in opcoes else [])


def _tratar_falha(exc: Exception):
    if isinstance(exc, ErroValidacao):
        st.session_state[PREFIXO + "erros"] = exc.erros
        st.rerun(scope="fragment")
    if isinstance(exc, ConflitoEdicao):
        st.session_state[PREFIXO + "conflito"] = str(exc)
        st.rerun(scope="fragment")
    if isinstance(exc, planilha.ErroPlanilha):
        st.session_state[PREFIXO + "conflito"] = str(exc)
        st.rerun(scope="fragment")
    raise exc


def _mostrar_conflito():
    msg = st.session_state.get(PREFIXO + "conflito")
    if msg:
        st.error(msg, icon=":material/sync_problem:")
        if st.button("Recarregar os dados da planilha", icon=":material/refresh:"):
            planilha.limpar_cache()
            _limpar_estado()
            st.rerun()


# --------------------------------------------------------------------------
# Assinatura
# --------------------------------------------------------------------------
def abrir_assinatura(id_: str | None = None):
    _limpar_estado()
    if id_ is None:
        _dialogo_nova_assinatura()
    else:
        original = planilha.ler_registro(ABA_ASSINATURAS, id_)  # leitura fresca (RF-16)
        if original is None:
            st.toast("Essa assinatura não existe mais na planilha.", icon=":material/warning:")
            planilha.limpar_cache()
            return
        st.session_state[PREFIXO + "original"] = original
        _dialogo_editar_assinatura()


@st.dialog("Nova assinatura", width="large")
def _dialogo_nova_assinatura():
    _form_assinatura(None)


@st.dialog("Editar assinatura", width="large")
def _dialogo_editar_assinatura():
    _form_assinatura(st.session_state.get(PREFIXO + "original"))


def _form_assinatura(original: dict | None):
    b = base()
    erros = st.session_state.get(PREFIXO + "erros", {})
    o = original or {}
    _mostrar_conflito()

    func = b.funcionarios
    ids = func["ID"].astype(str).tolist() if not func.empty else []
    nomes_por_id = dict(zip(ids, func["Nome completo"])) if ids else {}
    atuais = []
    if original:
        atuais = calc.usuarios_por_assinatura(func).get(str(o.get("Nome", "")), [])

    if not ids:
        st.warning("Cadastre pelo menos uma pessoa antes: toda assinatura precisa de 1 usuário.",
                   icon=":material/person_add:")

    with st.form(PREFIXO + "form_ass", border=False):
        c1, c2 = st.columns([2, 1])
        with c1:
            nome = st.text_input("Nome *", value=str(o.get("Nome", "") or ""), key=PREFIXO + "nome",
                                 max_chars=80, placeholder="Ex.: Figma")
            erro_campo(erros, "Nome")
        with c2:
            cats = _opcoes_com_atual(b.listas["Categorias"], o.get("Categoria"))
            categoria = st.selectbox("Categoria *", cats, index=_indice(cats, o.get("Categoria")),
                                     key=PREFIXO + "categoria", placeholder="Escolha")
            erro_campo(erros, "Categoria")

        logo = st.text_input("Logo (URL)", value=str(o.get("Logo (URL)", "") or ""), key=PREFIXO + "logo",
                             placeholder="https://...")
        erro_campo(erros, "Logo (URL)")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            planos = _opcoes_com_atual(b.listas["Planos"], o.get("Plano"))
            plano = st.selectbox("Plano *", planos, index=_indice(planos, o.get("Plano")),
                                 key=PREFIXO + "plano", placeholder="Escolha")
            erro_campo(erros, "Plano")
        with c2:
            valor_atual = calc.para_numero(o.get("Valor (R$)"))
            valor = st.number_input("Valor (R$) *", min_value=0.0, step=10.0, format="%.2f",
                                    value=valor_atual, key=PREFIXO + "valor", placeholder="0,00")
            erro_campo(erros, "Valor (R$)")
        with c3:
            venc = st.date_input("Vencimento", value=calc.para_data(o.get("Vencimento")),
                                 format="DD/MM/YYYY", key=PREFIXO + "venc",
                                 min_value=date(2000, 1, 1), max_value=date(2100, 12, 31),
                                 help="Data da próxima renovação. Só o plano Vitalício dispensa.")
            erro_campo(erros, "Vencimento")
        with c4:
            stts = _opcoes_com_atual(b.listas["Status"], o.get("Status"))
            status = st.selectbox("Status *", stts,
                                  index=_indice(stts, o.get("Status") or ("Ativa" if not original else "")),
                                  key=PREFIXO + "status", placeholder="Escolha")
            erro_campo(erros, "Status")

        usuarios = st.multiselect(
            "Usuários * (mínimo 1)", ids, default=[i for i in atuais if i in ids],
            format_func=lambda i: nomes_por_id.get(i, i), key=PREFIXO + "usuarios",
            placeholder="Escolha quem usa esta assinatura",
        )
        erro_campo(erros, "Usuários")
        st.caption("O nome não pode ter vírgula: a planilha usa vírgula para separar as escolhas.")

        salvar = st.form_submit_button("Salvar", type="primary", icon=":material/save:",
                                       disabled=not ids)

    if salvar:
        st.session_state.pop(PREFIXO + "erros", None)
        st.session_state.pop(PREFIXO + "conflito", None)
        dados = {"Nome": nome, "Logo (URL)": logo, "Categoria": categoria, "Plano": plano,
                 "Valor (R$)": valor, "Vencimento": venc, "Status": status}
        try:
            with st.spinner("Gravando na planilha..."):
                cadastros.salvar_assinatura(dados, usuarios, original)
        except Exception as exc:  # noqa: BLE001
            _tratar_falha(exc)
        avisar_depois(f"Assinatura “{nome.strip()}” salva.")
        _limpar_estado()
        st.rerun()


def confirmar_exclusao_assinatura(id_: str, nome: str, qtd_usuarios: int):
    _limpar_estado()
    st.session_state[PREFIXO + "excluir"] = (id_, nome, qtd_usuarios)
    _dialogo_excluir_assinatura()


@st.dialog("Excluir assinatura")
def _dialogo_excluir_assinatura():
    id_, nome, qtd = st.session_state[PREFIXO + "excluir"]
    _mostrar_conflito()
    st.markdown(f"Tem certeza que deseja excluir a assinatura **{nome}**?")
    if qtd:
        st.warning(f"Ela também será removida da lista de {qtd} pessoa(s).", icon=":material/group_remove:")
    st.caption("A exclusão fica registrada no Histórico. O histórico de versões do Google Sheets "
               "permite recuperar a linha, se necessário.")
    c1, c2 = st.columns(2)
    if c1.button("Cancelar", width="stretch"):
        _limpar_estado()
        st.rerun()
    if c2.button(f"Excluir {nome}", type="primary", icon=":material/delete:", width="stretch"):
        try:
            with st.spinner("Excluindo..."):
                cadastros.excluir_assinatura({"ID": id_})
        except Exception as exc:  # noqa: BLE001
            _tratar_falha(exc)
        avisar_depois(f"Assinatura “{nome}” excluída.", ":material/delete:")
        _limpar_estado()
        st.rerun()


def confirmar_pagamento_assinatura(id_: str):
    _limpar_estado()
    original = planilha.ler_registro(ABA_ASSINATURAS, id_)
    if original is None:
        st.toast("Essa assinatura não existe mais na planilha.", icon=":material/warning:")
        planilha.limpar_cache()
        return
    st.session_state[PREFIXO + "pagamento"] = original
    _dialogo_confirmar_pagamento()


@st.dialog("Marcar como pago")
def _dialogo_confirmar_pagamento():
    original = st.session_state.get(PREFIXO + "pagamento")
    if not original:
        return
    _mostrar_conflito()
    nome = str(original.get("Nome", "")).strip()
    plano = str(original.get("Plano", "")).strip()
    venc_atual = calc.para_data(original.get("Vencimento"))

    try:
        novo_venc = calc.avancar_vencimento(venc_atual, plano)
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc), icon=":material/error:")
        if st.button("Fechar", width="stretch"):
            _limpar_estado()
            st.rerun()
        return

    st.markdown(f"Deseja registrar o pagamento da assinatura **{nome}**?")

    c1, c2 = st.columns(2)
    with c1:
        st.caption("Plano")
        st.markdown(f"**{plano}**")
        st.caption("Vencimento atual")
        st.markdown(f"**{calc.formatar_data(venc_atual)}**")
    with c2:
        st.caption("Próximo vencimento")
        st.markdown(f"**:green[{calc.formatar_data(novo_venc)}]**")
        valor = calc.para_numero(original.get("Valor (R$)"))
        if valor is not None:
            st.caption("Valor da cobrança")
            st.markdown(f"**{calc.formatar_reais(valor)}**")

    st.caption("O próximo vencimento será avançado automaticamente e a operação ficará registrada no Histórico.")

    c1, c2 = st.columns(2)
    if c1.button("Cancelar", width="stretch"):
        _limpar_estado()
        st.rerun()
    if c2.button("Confirmar pagamento", type="primary", icon=":material/payments:", width="stretch"):
        try:
            with st.spinner("Registrando pagamento..."):
                cadastros.registrar_pagamento(str(original["ID"]), original)
        except Exception as exc:  # noqa: BLE001
            _tratar_falha(exc)
        avisar_depois(f"Pagamento de “{nome}” registrado. Próximo vencimento: {calc.formatar_data(novo_venc)}.", ":material/payments:")
        _limpar_estado()
        st.rerun()


# --------------------------------------------------------------------------
# Pessoa
# --------------------------------------------------------------------------
def abrir_pessoa(id_: str | None = None):
    _limpar_estado()
    if id_ is None:
        _dialogo_nova_pessoa()
    else:
        original = planilha.ler_registro(ABA_FUNCIONARIOS, id_)
        if original is None:
            st.toast("Essa pessoa não existe mais na planilha.", icon=":material/warning:")
            planilha.limpar_cache()
            return
        st.session_state[PREFIXO + "original"] = original
        _dialogo_editar_pessoa()


@st.dialog("Nova pessoa", width="large")
def _dialogo_nova_pessoa():
    _form_pessoa(None)


@st.dialog("Editar pessoa", width="large")
def _dialogo_editar_pessoa():
    _form_pessoa(st.session_state.get(PREFIXO + "original"))


def _form_pessoa(original: dict | None):
    b = base()
    erros = st.session_state.get(PREFIXO + "erros", {})
    o = original or {}
    _mostrar_conflito()

    opcoes = b.nomes_assinaturas
    escolhidas = calc.separar_lista(o.get("Assinaturas"))
    invalidas = [n for n in escolhidas if n not in opcoes]
    if invalidas:
        st.warning("Estas escolhas não existem mais como assinatura e serão removidas ao salvar: "
                   + ", ".join(invalidas), icon=":material/link_off:")

    with st.form(PREFIXO + "form_pessoa", border=False):
        c1, c2 = st.columns(2)
        with c1:
            nome = st.text_input("Nome completo *", value=str(o.get("Nome completo", "") or ""),
                                 key=PREFIXO + "nome", max_chars=120)
            erro_campo(erros, "Nome completo")
        with c2:
            email = st.text_input("E-mail *", value=str(o.get("E-mail", "") or ""), key=PREFIXO + "email",
                                  placeholder="nome@empresa.com.br")
            erro_campo(erros, "E-mail")
        c1, c2 = st.columns(2)
        with c1:
            deps = _opcoes_com_atual(b.listas["Departamentos"], o.get("Departamento"))
            dep = st.selectbox("Departamento *", deps, index=_indice(deps, o.get("Departamento")),
                               key=PREFIXO + "dep", placeholder="Escolha")
            erro_campo(erros, "Departamento")
        with c2:
            cargo = st.text_input("Cargo", value=str(o.get("Cargo", "") or ""), key=PREFIXO + "cargo")
        assinaturas = st.multiselect("Assinaturas", opcoes, default=[n for n in escolhidas if n in opcoes],
                                     key=PREFIXO + "assinaturas", placeholder="Escolha as ferramentas que a pessoa usa")
        salvar = st.form_submit_button("Salvar", type="primary", icon=":material/save:")

    if salvar:
        st.session_state.pop(PREFIXO + "erros", None)
        st.session_state.pop(PREFIXO + "conflito", None)
        dados = {"Nome completo": nome, "E-mail": email, "Departamento": dep, "Cargo": cargo}
        try:
            with st.spinner("Gravando na planilha..."):
                cadastros.salvar_pessoa(dados, assinaturas, original)
        except Exception as exc:  # noqa: BLE001
            _tratar_falha(exc)
        avisar_depois(f"{' '.join(nome.split())} salvo(a).")
        _limpar_estado()
        st.rerun()


def confirmar_exclusao_pessoa(id_: str, nome: str):
    _limpar_estado()
    st.session_state[PREFIXO + "excluir"] = (id_, nome)
    _dialogo_excluir_pessoa()


@st.dialog("Excluir pessoa")
def _dialogo_excluir_pessoa():
    id_, nome = st.session_state[PREFIXO + "excluir"]
    _mostrar_conflito()
    st.markdown(f"Tem certeza que deseja excluir **{nome}**?")
    st.caption("Os desvínculos das assinaturas ficam registrados no Histórico.")
    c1, c2 = st.columns(2)
    if c1.button("Cancelar", width="stretch"):
        _limpar_estado()
        st.rerun()


# --------------------------------------------------------------------------
# Projeto
# --------------------------------------------------------------------------
def abrir_projeto(id_: str | None = None):
    _limpar_estado()
    if id_ is None:
        st.session_state[PREFIXO + "projeto_original"] = None
        _dialogo_projeto()
        return
    original = planilha.ler_registro(ABA_PROJETOS, id_)
    if original is None:
        st.toast("Esse projeto não existe mais na planilha.", icon=":material/warning:")
        return
    st.session_state[PREFIXO + "projeto_original"] = original
    _dialogo_projeto()


@st.dialog("Projeto", width="large")
def _dialogo_projeto():
    original = st.session_state.get(PREFIXO + "projeto_original")
    o = original or {}
    erros = st.session_state.get(PREFIXO + "erros", {})
    _mostrar_conflito()
    b = base()
    ass_ids = b.assinaturas["ID"].astype(str).tolist() if not b.assinaturas.empty else []
    nomes = dict(zip(ass_ids, b.assinaturas["Nome"].astype(str)))
    atuais = []
    if original and not b.usos_projeto.empty:
        atuais = b.usos_projeto[
            b.usos_projeto["Projeto ID"].astype(str) == str(original["ID"])
        ]["Assinatura ID"].astype(str).tolist()

    with st.form(PREFIXO + "form_projeto", border=False):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome do projeto *", value=str(o.get("Nome", "") or ""))
        cliente = c2.text_input("Cliente", value=str(o.get("Cliente", "") or ""))
        erro_campo(erros, "Nome")
        c1, c2 = st.columns(2)
        responsavel = c1.text_input("Responsável", value=str(o.get("Responsável", "") or ""))
        deps = _opcoes_com_atual(b.listas["Departamentos"], o.get("Departamento"))
        departamento = c2.selectbox("Departamento", deps, index=_indice(deps, o.get("Departamento")),
                                    placeholder="Escolha")
        status_op = _opcoes_com_atual(["Ativo", "Pausado"], o.get("Status"))
        status = st.selectbox("Status *", status_op,
                              index=_indice(status_op, o.get("Status") or "Ativo"))
        escolhidas = st.multiselect("Assinaturas usadas no projeto *", ass_ids,
                                    default=[i for i in atuais if i in ass_ids],
                                    format_func=lambda i: nomes.get(i, i),
                                    placeholder="Selecione uma ou mais assinaturas")
        erro_campo(erros, "Assinaturas")
        observacoes = st.text_area("Observações", value=str(o.get("Observações", "") or ""))
        salvar = st.form_submit_button("Salvar projeto", type="primary", icon=":material/save:")
    if salvar:
        dados = {"Nome": nome, "Cliente": cliente, "Responsável": responsavel,
                 "Departamento": departamento,
                 "Status": status, "Observações": observacoes}
        try:
            cadastros.salvar_projeto(dados, escolhidas, original)
        except Exception as exc:  # noqa: BLE001
            _tratar_falha(exc)
        avisar_depois(f"Projeto “{nome.strip()}” salvo.")
        _limpar_estado()
        st.rerun()


def confirmar_exclusao_projeto(original: dict):
    st.session_state[PREFIXO + "excluir_projeto"] = original
    _dialogo_excluir_projeto()


def confirmar_conclusao_projeto(original: dict):
    st.session_state[PREFIXO + "concluir_projeto"] = original
    _dialogo_concluir_projeto()


@st.dialog("Concluir projeto")
def _dialogo_concluir_projeto():
    original = st.session_state[PREFIXO + "concluir_projeto"]
    st.markdown(f"Deseja marcar o projeto **{original['Nome']}** como concluído?")
    st.caption("Ele continuará disponível para consulta, mas deixará de participar da divisão dos custos ativos.")
    c1, c2 = st.columns(2)
    if c1.button("Cancelar", width="stretch"):
        _limpar_estado()
        st.rerun()
    if c2.button("Marcar como concluído", type="primary", icon=":material/task_alt:", width="stretch"):
        try:
            cadastros.concluir_projeto(original)
        except Exception as exc:  # noqa: BLE001
            _tratar_falha(exc)
        avisar_depois(f"Projeto “{original['Nome']}” concluído.", ":material/task_alt:")
        _limpar_estado()
        st.rerun()


@st.dialog("Excluir projeto")
def _dialogo_excluir_projeto():
    original = st.session_state[PREFIXO + "excluir_projeto"]
    st.warning(f"Excluir o projeto **{original['Nome']}** e todos os seus vínculos?", icon=":material/warning:")
    c1, c2 = st.columns(2)
    if c1.button("Cancelar", width="stretch"):
        _limpar_estado()
        st.rerun()
    if c2.button("Excluir projeto", type="primary", icon=":material/delete:", width="stretch"):
        try:
            cadastros.excluir_projeto(original)
        except Exception as exc:  # noqa: BLE001
            _tratar_falha(exc)
        avisar_depois("Projeto excluído.", ":material/delete:")
        _limpar_estado()
        st.rerun()
    if c2.button(f"Excluir {nome.split()[0] if nome.split() else ''}", type="primary",
                 icon=":material/delete:", width="stretch"):
        try:
            with st.spinner("Excluindo..."):
                cadastros.excluir_pessoa({"ID": id_})
        except Exception as exc:  # noqa: BLE001
            _tratar_falha(exc)
        avisar_depois(f"{nome} excluído(a).", ":material/delete:")
        _limpar_estado()
        st.rerun()


# --------------------------------------------------------------------------
# Linha do tempo (RF-24)
# --------------------------------------------------------------------------
ICONE_EVENTO = {
    "Assinatura criada": "✨", "Valor alterado": "💲", "Plano alterado": "🔁",
    "Status alterado": "🔘", "Usuário vinculado": "➕", "Usuário desvinculado": "➖",
    "Assinatura renomeada": "✏️", "Assinatura excluída": "🗑️",
    "Pagamento registrado": "💳",
}


def descrever(evento: pd.Series) -> str:
    ant, novo = str(evento.get("Valor anterior", "") or ""), str(evento.get("Valor novo", "") or "")
    campo = str(evento.get("Campo", "") or "")
    if campo == "Valor (R$)":
        a, n = calc.para_numero(ant), calc.para_numero(novo)
        ant = calc.formatar_reais(a) if a is not None else ant
        novo = calc.formatar_reais(n) if n is not None else novo
    ev = str(evento.get("Evento", ""))
    if ev == "Pagamento registrado" or campo == "Vencimento":
        a, n = calc.para_data(ant), calc.para_data(novo)
        ant_txt = calc.formatar_data(a) if a else ant
        novo_txt = calc.formatar_data(n) if n else novo
        return f"{ant_txt or '(vazio)'} → {novo_txt or '(vazio)'}"
    if ev == "Usuário vinculado":
        return f"{novo} passou a usar"
    if ev == "Usuário desvinculado":
        return f"{ant} deixou de usar"
    if ev == "Assinatura criada":
        return novo
    if ant or novo:
        return f"{ant or '(vazio)'} → {novo or '(vazio)'}"
    return ""


def linha_do_tempo_html(df: pd.DataFrame, mostrar_assinatura: bool = False) -> str:
    import html
    itens = []
    for _, e in df.iterrows():
        quando = calc.para_datahora(e["Data e hora"])
        q = quando.strftime("%d/%m/%Y %H:%M") if quando else str(e["Data e hora"])
        origem = "📄 planilha" if str(e["Origem"]).strip().lower() == "planilha" else "🖥️ app"
        quem = str(e.get("Quem", "") or "")
        ev = str(e["Evento"])
        itens.append(
            "<div class='ga-tl-item'>"
            f"<div class='ga-tl-data'>{html.escape(q)} · {origem}{' · ' + html.escape(quem) if quem else ''}</div>"
            f"<div class='ga-tl-ev'>{ICONE_EVENTO.get(ev, '•')} "
            f"{html.escape(str(e['Assinatura']) + ' — ' if mostrar_assinatura else '')}{html.escape(ev)}</div>"
            f"<div class='ga-tl-det'>{html.escape(descrever(e))}</div></div>"
        )
    return "<div class='ga-tl'>" + "".join(itens) + "</div>"


def abrir_linha_do_tempo(nome: str):
    _limpar_estado()
    st.session_state[PREFIXO + "tl"] = nome
    _dialogo_linha_do_tempo()


@st.dialog("Linha do tempo", width="large")
def _dialogo_linha_do_tempo():
    nome = st.session_state[PREFIXO + "tl"]
    hist = base().historico
    st.markdown(f"### {nome}")
    if hist.empty:
        st.info("Nenhum registro no Histórico ainda.")
        return
    df = hist[hist["Assinatura"].astype(str) == nome].copy()
    if df.empty:
        st.info("Nenhum registro no Histórico para esta assinatura.")
        return
    df["_q"] = pd.to_datetime(df["Data e hora"].map(calc.para_datahora), errors="coerce")
    df = df.sort_values("_q", ascending=False)
    visivel = limitar_itens(df, "dlg_linha_tempo")
    st.caption(f"Mostrando {len(visivel)} de {len(df)} registro(s), do mais recente para o mais antigo")
    st.html(linha_do_tempo_html(visivel))
    controle_ver_mais(len(df), len(visivel), "dlg_linha_tempo")
