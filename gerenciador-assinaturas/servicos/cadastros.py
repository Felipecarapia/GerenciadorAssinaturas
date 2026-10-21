"""Operações de cadastro: validação, vínculos nos dois sentidos, histórico
e proteção contra edição simultânea (RF-12 a RF-16, RF-18 a RF-23)."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import streamlit as st

from servicos import planilha
from servicos.calculos import (
    avancar_vencimento, email_valido, formatar_data, formatar_reais, normalizar, para_data, para_datahora, para_numero, vazio,
)
from servicos.esquema import (
    ABA_EQUIPE, ABA_ASSINATURAS, ABA_FUNCIONARIOS, ABA_HISTORICO, ABA_PROJETOS,
    COLUNAS, EV_CRIADA, EV_EXCLUIDA, EV_PAGAMENTO, EVENTO_POR_CAMPO,
)


class ConflitoEdicao(Exception):
    """Alguém alterou o mesmo registro na planilha enquanto a janela estava aberta."""


class TransicaoInvalida(Exception):
    """A mudança solicitada não é permitida no estado atual do projeto."""


class ErroValidacao(Exception):
    def __init__(self, erros: dict[str, str]):
        super().__init__("; ".join(erros.values()))
        self.erros = erros


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def fuso() -> ZoneInfo:
    try:
        return ZoneInfo(st.secrets.get("app", {}).get("fuso", "America/Bahia"))
    except Exception:
        return ZoneInfo("America/Bahia")


def agora() -> datetime:
    return datetime.now(fuso()).replace(tzinfo=None, microsecond=0)


def hoje() -> date:
    return agora().date()


def quem() -> str:
    """No Community Cloud, o e-mail do convidado; senão, 'app'."""
    from servicos.usuarios import usuario_atual

    usuario = usuario_atual.get()
    if usuario is not None and usuario.email:
        return usuario.email
    try:
        email = st.user.get("email") if hasattr(st.user, "get") else getattr(st.user, "email", None)
        if email and "@" in str(email) and "example.com" not in str(email):
            return str(email)
    except Exception:
        pass
    return "app"


def _norm(v, campo: str = "") -> str:
    if vazio(v):
        return ""
    if isinstance(v, bool):
        return str(v)
    if campo in {"Cadastrado em", "Solicitado em", "Aprovado em", "Recusado em", "Proposto em", "Último acesso"}:
        datahora = para_datahora(v)
        return datahora.strftime("%Y-%m-%d %H:%M:%S") if datahora else str(v).strip()
    if campo in {"Vencimento", "Data de início", "Data de término"}:
        data = para_data(v)
        return data.isoformat() if data else str(v).strip()
    if isinstance(v, (int, float)):
        return f"{float(v):.4f}"
    return str(v).strip()


def _sem_internos(reg: dict, aba: str) -> dict:
    return {c: reg.get(c, "") for c in COLUNAS[aba]}


def _verificar_conflito(aba: str, original: dict) -> dict:
    """RF-16: relê a linha e compara com o que o usuário abriu na janela."""
    atual = planilha.ler_registro(aba, original["ID"])
    if atual is None:
        raise ConflitoEdicao("Esse registro foi excluído da planilha enquanto você editava.")
    diferentes = [c for c in COLUNAS[aba] if _norm(atual.get(c), c) != _norm(original.get(c), c)]
    if diferentes:
        raise ConflitoEdicao(
            "Alguém alterou este registro na planilha enquanto você editava "
            f"({', '.join(diferentes)}). Feche a janela, clique em Atualizar e refaça a edição."
        )
    return atual


def _evento(assinatura, evento, campo="", anterior="", novo="", quando=None) -> dict:
    return {
        "Data e hora": (quando or agora()).strftime("%Y-%m-%d %H:%M:%S"),
        "Origem": "app", "Quem": quem(), "Assinatura": assinatura, "Evento": evento,
        "Campo": campo, "Valor anterior": "" if vazio(anterior) else str(anterior),
        "Valor novo": "" if vazio(novo) else str(novo),
    }


def _texto_hist(campo, v):
    if campo == "Valor (R$)":
        n = para_numero(v)
        return "" if n is None else f"{n:.2f}"
    return "" if vazio(v) else str(v)


def registrar(eventos: list[dict]):
    if eventos:
        planilha.inserir(ABA_HISTORICO, eventos)


# --------------------------------------------------------------------------
# Assinaturas
# --------------------------------------------------------------------------
def validar_assinatura(dados: dict, df_ass, id_atual=None) -> dict[str, str]:
    """RF-13: obrigatórios, valor positivo, nome sem vírgula e único."""
    erros = {}
    nome = str(dados.get("Nome", "")).strip()
    if not nome:
        erros["Nome"] = "Informe o nome."
    elif "," in nome:
        erros["Nome"] = "O nome não pode ter vírgula (a planilha separa as escolhas por vírgula)."
    else:
        outros = df_ass if id_atual is None else df_ass[df_ass["ID"].astype(str) != str(id_atual)]
        if not outros.empty and normalizar(nome) in set(outros["Nome"].map(normalizar)):
            erros["Nome"] = "Já existe uma assinatura com esse nome."
    for campo in ("Categoria", "Plano", "Status"):
        if vazio(dados.get(campo)):
            erros[campo] = f"Escolha {campo.lower()}."
    valor = para_numero(dados.get("Valor (R$)"))
    if valor is None:
        erros["Valor (R$)"] = "Informe o valor."
    elif valor <= 0:
        erros["Valor (R$)"] = "O valor precisa ser maior que zero."
    if normalizar(dados.get("Plano")) not in ("vitalício", "vitalicio") and not dados.get("Vencimento"):
        erros["Vencimento"] = "Informe o vencimento (só o plano Vitalício dispensa)."
    logo = str(dados.get("Logo (URL)", "") or "").strip()
    if logo and not logo.startswith(("http://", "https://")):
        erros["Logo (URL)"] = "O logo precisa ser um link começando com https://"
    return erros


def salvar_assinatura(dados: dict, original: dict | None = None) -> str:
    """Cria ou edita uma assinatura e recalcula as colunas derivadas da equipe.

    `original` é a linha como estava quando a janela foi aberta (None = nova).
    Retorna o ID salvo.
    """
    df_ass = planilha.ler_fresco(ABA_ASSINATURAS)
    erros = validar_assinatura(dados, df_ass, original["ID"] if original else None)
    if erros:
        raise ErroValidacao(erros)

    momento = agora()
    eventos = []
    registro = {
        "Nome": str(dados["Nome"]).strip(),
        "Logo (URL)": str(dados.get("Logo (URL)") or "").strip(),
        "Categoria": dados["Categoria"], "Plano": dados["Plano"],
        "Valor (R$)": round(float(para_numero(dados["Valor (R$)"])), 2),
        "Vencimento": dados["Vencimento"].isoformat() if dados.get("Vencimento") else "",
        "Status": dados["Status"],
    }

    if original is None:
        id_ = planilha.novo_id(ABA_ASSINATURAS)
        registro |= {"ID": id_, "Cadastrado em": momento.strftime("%Y-%m-%d %H:%M:%S")}
        planilha.inserir(ABA_ASSINATURAS, [registro])
        eventos.append(_evento(registro["Nome"], EV_CRIADA, "", "",
                               f"{registro['Plano']} · {formatar_reais(registro['Valor (R$)'])} · {registro['Status']}",
                               momento))
    else:
        atual = _verificar_conflito(ABA_ASSINATURAS, original)
        id_ = str(original["ID"])
        cad = atual.get("Cadastrado em")
        registro |= {"ID": id_, "Cadastrado em": cad if not vazio(cad) else momento.strftime("%Y-%m-%d %H:%M:%S")}
        if isinstance(registro["Cadastrado em"], (int, float)):
            from servicos.calculos import para_datahora
            registro["Cadastrado em"] = para_datahora(registro["Cadastrado em"]).strftime("%Y-%m-%d %H:%M:%S")
        planilha.atualizar(ABA_ASSINATURAS, id_, registro)
        for campo, evento in EVENTO_POR_CAMPO.items():
            antes, depois = _texto_hist(campo, atual.get(campo)), _texto_hist(campo, registro[campo])
            if normalizar(antes) != normalizar(depois):
                eventos.append(_evento(registro["Nome"], evento, campo, antes, depois, momento))

    registrar(eventos)
    from servicos.projetos import sincronizar_derivados
    sincronizar_derivados()
    return id_


def _limpar_datas(reg: dict) -> dict:
    """Converte números de série de data (do Sheets) de volta para texto ISO."""
    from servicos.calculos import para_datahora
    v = reg.get("Cadastrado em")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        dh = para_datahora(v)
        reg["Cadastrado em"] = dh.strftime("%Y-%m-%d %H:%M:%S") if dh else ""
    return reg


def excluir_assinatura(original: dict):
    """RF-15: exclui e tira o nome da lista de cada funcionário."""
    atual = planilha.ler_registro(ABA_ASSINATURAS, original["ID"])
    if atual is None:
        planilha.limpar_cache()
        return
    nome = str(atual["Nome"])
    momento = agora()
    equipe = planilha.ler_fresco(ABA_EQUIPE)
    projetos = planilha.ler_fresco(ABA_PROJETOS)
    nomes_projetos = dict(zip(projetos["ID"].astype(str), projetos["Nome"].astype(str))) if not projetos.empty else {}
    status_projetos = dict(zip(projetos["ID"].astype(str), projetos["Status"].map(normalizar))) if not projetos.empty else {}
    vinculadas = equipe[equipe["Assinatura ID"].astype(str) == str(original["ID"])] if not equipe.empty else equipe
    abertos = sorted({nomes_projetos.get(str(l["Projeto ID"]), str(l["Projeto ID"])) for _, l in vinculadas.iterrows()
                      if status_projetos.get(str(l["Projeto ID"])) != "concluído"})
    if abertos:
        raise ErroValidacao({"Assinatura": "Remova a assinatura dos projetos antes de excluí-la: " + ", ".join(abertos)})
    for _, linha in vinculadas.iterrows():
        planilha.excluir(ABA_EQUIPE, str(linha["ID"]))
    planilha.excluir(ABA_ASSINATURAS, original["ID"])
    registrar([_evento(nome, EV_EXCLUIDA, "", nome, "", momento)])
    from servicos.projetos import sincronizar_derivados
    sincronizar_derivados(permitir_equipe_vazia=not equipe.empty)


def registrar_pagamento(id_assinatura: str, original: dict | None = None) -> date:
    """Registra o pagamento de uma assinatura: avança o vencimento e grava no Histórico.

    Se `original` for fornecido, verifica conflito de edição simultânea (RF-16).
    """
    if original is not None:
        atual = _verificar_conflito(ABA_ASSINATURAS, original)
    else:
        atual = planilha.ler_registro(ABA_ASSINATURAS, id_assinatura)
        if atual is None:
            raise ErroValidacao({"ID": "Assinatura não encontrada na planilha."})

    plano = str(atual.get("Plano", ""))
    venc_antigo = atual.get("Vencimento")
    venc_data = para_data(venc_antigo)
    if venc_data is None:
        raise ErroValidacao({"Vencimento": "A assinatura não possui data de vencimento válida."})

    novo_venc = avancar_vencimento(venc_data, plano)
    momento = agora()

    # Pagamento não deve regravar campos que não fazem parte da operação.
    planilha.atualizar_campos(
        ABA_ASSINATURAS, str(atual["ID"]), {"Vencimento": novo_venc.isoformat()}
    )

    ant_str = formatar_data(venc_data)
    novo_str = formatar_data(novo_venc)
    evento = _evento(
        assinatura=str(atual.get("Nome", "")).strip(),
        evento=EV_PAGAMENTO,
        campo="Vencimento",
        anterior=ant_str,
        novo=novo_str,
        quando=momento,
    )
    registrar([evento])
    planilha.limpar_cache()
    return novo_venc


# --------------------------------------------------------------------------
# Pessoas
# --------------------------------------------------------------------------
def validar_pessoa(dados: dict, df_func, id_atual=None) -> dict[str, str]:
    """RF-19: e-mail único e válido + obrigatórios."""
    erros = {}
    if not str(dados.get("Nome completo", "")).strip():
        erros["Nome completo"] = "Informe o nome completo."
    email = str(dados.get("E-mail", "")).strip()
    if not email:
        erros["E-mail"] = "Informe o e-mail."
    elif not email_valido(email):
        erros["E-mail"] = "E-mail inválido. Use o formato nome@empresa.com.br"
    else:
        outros = df_func if id_atual is None else df_func[df_func["ID"].astype(str) != str(id_atual)]
        if not outros.empty and email.casefold() in set(outros["E-mail"].astype(str).str.strip().str.casefold()):
            erros["E-mail"] = "Esse e-mail já está cadastrado para outra pessoa."
    if vazio(dados.get("Departamento")):
        erros["Departamento"] = "Escolha o departamento."
    return erros


def salvar_pessoa(dados: dict, original: dict | None = None) -> str:
    df_func = planilha.ler_fresco(ABA_FUNCIONARIOS)
    erros = validar_pessoa(dados, df_func, original["ID"] if original else None)
    if erros:
        raise ErroValidacao(erros)
    momento = agora()
    registro = {
        "Nome completo": " ".join(str(dados["Nome completo"]).split()),
        "E-mail": str(dados["E-mail"]).strip().lower(),
        "Departamento": dados["Departamento"],
        "Cargo": str(dados.get("Cargo") or "").strip(),
        "Assinaturas": "",
    }
    if original is None:
        id_ = planilha.novo_id(ABA_FUNCIONARIOS)
        registro |= {"ID": id_, "Cadastrado em": momento.strftime("%Y-%m-%d %H:%M:%S")}
        planilha.inserir(ABA_FUNCIONARIOS, [registro])
    else:
        atual = _verificar_conflito(ABA_FUNCIONARIOS, original)
        id_ = str(original["ID"])
        registro |= {"ID": id_, "Cadastrado em": atual.get("Cadastrado em", ""),
                     "Assinaturas": atual.get("Assinaturas", "")}
        registro = _limpar_datas(registro)
        planilha.atualizar(ABA_FUNCIONARIOS, id_, registro)
    planilha.limpar_cache()
    return id_


def excluir_pessoa(original: dict):
    atual = planilha.ler_registro(ABA_FUNCIONARIOS, original["ID"])
    if atual is None:
        planilha.limpar_cache()
        return
    equipe = planilha.ler_fresco(ABA_EQUIPE)
    projetos = planilha.ler_fresco(ABA_PROJETOS)
    nomes = dict(zip(projetos["ID"].astype(str), projetos["Nome"].astype(str))) if not projetos.empty else {}
    status = dict(zip(projetos["ID"].astype(str), projetos["Status"].map(normalizar))) if not projetos.empty else {}
    vinculadas = equipe[equipe["Pessoa ID"].astype(str) == str(original["ID"])] if not equipe.empty else equipe
    abertos = sorted({nomes.get(str(l["Projeto ID"]), str(l["Projeto ID"])) for _, l in vinculadas.iterrows()
                      if status.get(str(l["Projeto ID"])) != "concluído"})
    if abertos:
        raise ErroValidacao({"Pessoa": "Conclua ou remova a pessoa destes projetos antes de excluí-la: " + ", ".join(abertos)})
    for _, linha in vinculadas.iterrows():
        planilha.excluir(ABA_EQUIPE, str(linha["ID"]))
    planilha.excluir(ABA_FUNCIONARIOS, original["ID"])
    planilha.limpar_cache()
