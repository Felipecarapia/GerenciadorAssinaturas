"""Operações de cadastro: validação, vínculos nos dois sentidos, histórico
e proteção contra edição simultânea (RF-12 a RF-16, RF-18 a RF-23)."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import streamlit as st

from servicos import planilha
from servicos.calculos import (
    avancar_vencimento, email_valido, formatar_data, formatar_reais, juntar_lista, normalizar, para_data, para_numero, separar_lista, vazio,
)
from servicos.esquema import (
    ABA_ASSINATURAS, ABA_FUNCIONARIOS, ABA_HISTORICO, ABA_PROJETOS, ABA_USOS_PROJETO,
    COLUNAS, EV_CRIADA, EV_DESVINCULADO, EV_EXCLUIDA, EV_PAGAMENTO, EV_VINCULADO,
    EV_PROJETO_ALTERADO, EV_PROJETO_CONCLUIDO, EV_PROJETO_CRIADO, EV_PROJETO_DESVINCULADO,
    EV_PROJETO_EXCLUIDO, EV_PROJETO_VINCULADO, EVENTO_POR_CAMPO,
)


class ConflitoEdicao(Exception):
    """Alguém alterou o mesmo registro na planilha enquanto a janela estava aberta."""


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
    try:
        email = st.user.get("email") if hasattr(st.user, "get") else getattr(st.user, "email", None)
        if email and "@" in str(email) and "example.com" not in str(email):
            return str(email)
    except Exception:
        pass
    return "app"


def _norm(v) -> str:
    if vazio(v):
        return ""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        return f"{float(v):.4f}"
    d = para_data(v) if not isinstance(v, str) else None
    if d:
        return d.isoformat()
    return str(v).strip()


def _sem_internos(reg: dict, aba: str) -> dict:
    return {c: reg.get(c, "") for c in COLUNAS[aba]}


def _verificar_conflito(aba: str, original: dict) -> dict:
    """RF-16: relê a linha e compara com o que o usuário abriu na janela."""
    atual = planilha.ler_registro(aba, original["ID"])
    if atual is None:
        raise ConflitoEdicao("Esse registro foi excluído da planilha enquanto você editava.")
    diferentes = [c for c in COLUNAS[aba] if _norm(atual.get(c)) != _norm(original.get(c))]
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
def validar_assinatura(dados: dict, usuarios: list[str], df_ass, id_atual=None) -> dict[str, str]:
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
    if not usuarios:
        erros["Usuários"] = "Escolha pelo menos 1 usuário."
    return erros


def salvar_assinatura(dados: dict, usuarios_ids: list[str], original: dict | None = None) -> str:
    """Cria ou edita uma assinatura e sincroniza a coluna Assinaturas dos funcionários.

    `original` é a linha como estava quando a janela foi aberta (None = nova).
    Retorna o ID salvo.
    """
    df_ass = planilha.ler_fresco(ABA_ASSINATURAS)
    erros = validar_assinatura(dados, usuarios_ids, df_ass, original["ID"] if original else None)
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
        nome_antigo = None
    else:
        atual = _verificar_conflito(ABA_ASSINATURAS, original)
        id_ = str(original["ID"])
        cad = atual.get("Cadastrado em")
        registro |= {"ID": id_, "Cadastrado em": cad if not vazio(cad) else momento.strftime("%Y-%m-%d %H:%M:%S")}
        if isinstance(registro["Cadastrado em"], (int, float)):
            from servicos.calculos import para_datahora
            registro["Cadastrado em"] = para_datahora(registro["Cadastrado em"]).strftime("%Y-%m-%d %H:%M:%S")
        planilha.atualizar(ABA_ASSINATURAS, id_, registro)
        nome_antigo = str(atual["Nome"])
        for campo, evento in EVENTO_POR_CAMPO.items():
            antes, depois = _texto_hist(campo, atual.get(campo)), _texto_hist(campo, registro[campo])
            if normalizar(antes) != normalizar(depois):
                eventos.append(_evento(registro["Nome"], evento, campo, antes, depois, momento))

    eventos += _sincronizar_usuarios(registro["Nome"], nome_antigo, usuarios_ids, momento)
    registrar(eventos)
    planilha.limpar_cache()
    return id_


def _sincronizar_usuarios(nome: str, nome_antigo: str | None, usuarios_ids: list[str], momento) -> list[dict]:
    """RF-14 e vínculos: atualiza a coluna Assinaturas de cada funcionário."""
    df_func = planilha.ler_fresco(ABA_FUNCIONARIOS)
    desejados = {str(i) for i in usuarios_ids}
    alterar, eventos = {}, []
    for _, f in df_func.iterrows():
        id_f = str(f["ID"])
        lista = separar_lista(f["Assinaturas"])
        nova = list(lista)
        if nome_antigo and nome_antigo != nome:
            nova = [nome if n == nome_antigo else n for n in nova]
        tem = nome in nova
        if id_f in desejados and not tem:
            nova.append(nome)
            eventos.append(_evento(nome, EV_VINCULADO, "Usuários", "", f["Nome completo"], momento))
        elif id_f not in desejados and tem:
            nova = [n for n in nova if n != nome]
            eventos.append(_evento(nome, EV_DESVINCULADO, "Usuários", f["Nome completo"], "", momento))
        if nova != lista:
            reg = _sem_internos(f.to_dict(), ABA_FUNCIONARIOS)
            reg["Assinaturas"] = juntar_lista(nova)
            alterar[id_f] = _limpar_datas(reg)
    planilha.atualizar_varios(ABA_FUNCIONARIOS, alterar)
    return eventos


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
    eventos = _sincronizar_usuarios(nome, None, [], momento)
    usos = planilha.ler_fresco(ABA_USOS_PROJETO)
    vinculados = usos[usos["Assinatura ID"].astype(str) == str(original["ID"])] if not usos.empty else usos
    projetos = planilha.ler_fresco(ABA_PROJETOS)
    nomes_projetos = dict(zip(projetos["ID"].astype(str), projetos["Nome"].astype(str))) if not projetos.empty else {}
    for _, uso in vinculados.iterrows():
        planilha.excluir(ABA_USOS_PROJETO, str(uso["ID"]))
        eventos.append(_evento(nome, EV_PROJETO_DESVINCULADO, "Projeto",
                               nomes_projetos.get(str(uso["Projeto ID"]), str(uso["Projeto ID"])), "", momento))
    planilha.excluir(ABA_ASSINATURAS, original["ID"])
    eventos.append(_evento(nome, EV_EXCLUIDA, "", nome, "", momento))
    registrar(eventos)
    planilha.limpar_cache()


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


def salvar_pessoa(dados: dict, assinaturas: list[str], original: dict | None = None) -> str:
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
        "Assinaturas": juntar_lista(assinaturas),
    }
    if original is None:
        id_ = planilha.novo_id(ABA_FUNCIONARIOS)
        registro |= {"ID": id_, "Cadastrado em": momento.strftime("%Y-%m-%d %H:%M:%S")}
        planilha.inserir(ABA_FUNCIONARIOS, [registro])
        antes = []
    else:
        atual = _verificar_conflito(ABA_FUNCIONARIOS, original)
        id_ = str(original["ID"])
        registro |= {"ID": id_, "Cadastrado em": atual.get("Cadastrado em", "")}
        registro = _limpar_datas(registro)
        planilha.atualizar(ABA_FUNCIONARIOS, id_, registro)
        antes = separar_lista(atual.get("Assinaturas"))
    depois = separar_lista(registro["Assinaturas"])
    eventos = [_evento(a, EV_VINCULADO, "Usuários", "", registro["Nome completo"], momento)
               for a in depois if a not in antes]
    eventos += [_evento(a, EV_DESVINCULADO, "Usuários", registro["Nome completo"], "", momento)
                for a in antes if a not in depois]
    registrar(eventos)
    planilha.limpar_cache()
    return id_


def excluir_pessoa(original: dict):
    atual = planilha.ler_registro(ABA_FUNCIONARIOS, original["ID"])
    if atual is None:
        planilha.limpar_cache()
        return
    momento = agora()
    eventos = [_evento(a, EV_DESVINCULADO, "Usuários", atual["Nome completo"], "", momento)
               for a in separar_lista(atual.get("Assinaturas"))]
    planilha.excluir(ABA_FUNCIONARIOS, original["ID"])
    registrar(eventos)
    planilha.limpar_cache()


def remover_escolhas_invalidas(id_func: str, nomes_validos: set[str]) -> list[str]:
    """Pendências: tira da pessoa as assinaturas que não existem mais."""
    atual = planilha.ler_registro(ABA_FUNCIONARIOS, id_func)
    if atual is None:
        return []
    lista = separar_lista(atual.get("Assinaturas"))
    invalidas = [n for n in lista if n not in nomes_validos]
    if invalidas:
        reg = _limpar_datas(_sem_internos(atual, ABA_FUNCIONARIOS))
        reg["Assinaturas"] = juntar_lista([n for n in lista if n in nomes_validos])
        planilha.atualizar(ABA_FUNCIONARIOS, id_func, reg)
        planilha.limpar_cache()
    return invalidas


# --------------------------------------------------------------------------
# Projetos e uso de assinaturas
# --------------------------------------------------------------------------
def validar_projeto(dados: dict, assinaturas_ids: list[str], df_projetos, id_atual=None) -> dict[str, str]:
    erros = {}
    nome = str(dados.get("Nome", "")).strip()
    if not nome:
        erros["Nome"] = "Informe o nome do projeto."
    else:
        outros = df_projetos if id_atual is None else df_projetos[df_projetos["ID"].astype(str) != str(id_atual)]
        if not outros.empty and normalizar(nome) in set(outros["Nome"].map(normalizar)):
            erros["Nome"] = "Já existe um projeto com esse nome."
    if vazio(dados.get("Status")):
        erros["Status"] = "Escolha o status."
    if not assinaturas_ids:
        erros["Assinaturas"] = "Vincule pelo menos uma assinatura."
    return erros


def salvar_projeto(dados: dict, assinaturas_ids: list[str], original: dict | None = None) -> str:
    projetos = planilha.ler_fresco(ABA_PROJETOS)
    erros = validar_projeto(dados, assinaturas_ids, projetos, original["ID"] if original else None)
    if erros:
        raise ErroValidacao(erros)
    momento = agora()
    registro = {
        "Nome": " ".join(str(dados["Nome"]).split()), "Cliente": str(dados.get("Cliente") or "").strip(),
        "Responsável": str(dados.get("Responsável") or "").strip(),
        "Departamento": str(dados.get("Departamento") or "").strip(),
        # Mantidos vazios na planilha para compatibilidade com a estrutura existente.
        "Data de início": "", "Data de término": "",
        "Status": dados["Status"], "Observações": str(dados.get("Observações") or "").strip(),
    }
    if original is None:
        id_ = planilha.novo_id(ABA_PROJETOS)
        registro |= {"ID": id_, "Cadastrado em": momento.strftime("%Y-%m-%d %H:%M:%S")}
        planilha.inserir(ABA_PROJETOS, [registro])
        eventos = [_evento(registro["Nome"], EV_PROJETO_CRIADO, "Projeto", "", registro["Nome"], momento)]
    else:
        atual = _verificar_conflito(ABA_PROJETOS, original)
        id_ = str(atual["ID"])
        registro |= {"ID": id_, "Cadastrado em": atual.get("Cadastrado em", "")}
        planilha.atualizar(ABA_PROJETOS, id_, _limpar_datas(registro))
        eventos = [_evento(registro["Nome"], EV_PROJETO_ALTERADO, "Projeto", atual.get("Nome", ""), registro["Nome"], momento)]

    usos = planilha.ler_fresco(ABA_USOS_PROJETO)
    atuais = usos[usos["Projeto ID"].astype(str) == id_] if not usos.empty else usos
    por_ass = {str(r["Assinatura ID"]): r.to_dict() for _, r in atuais.iterrows()}
    desejados = set(map(str, assinaturas_ids))
    nomes_ass = dict(zip(planilha.ler_fresco(ABA_ASSINATURAS)["ID"].astype(str),
                         planilha.ler_fresco(ABA_ASSINATURAS)["Nome"].astype(str)))
    novos = []
    for ass_id in desejados - set(por_ass):
        novos.append({
            "ID": planilha.novo_id(ABA_USOS_PROJETO), "Projeto ID": id_, "Assinatura ID": ass_id,
            "Finalidade": "", "Responsável": registro["Responsável"],
            "Data de início": "", "Data de término": "", "Status": "Ativo",
            "Observações": "", "Cadastrado em": momento.strftime("%Y-%m-%d %H:%M:%S"),
        })
        eventos.append(_evento(nomes_ass.get(ass_id, ass_id), EV_PROJETO_VINCULADO, "Projeto", "", registro["Nome"], momento))
    if novos:
        planilha.inserir(ABA_USOS_PROJETO, novos)
    for ass_id in set(por_ass) - desejados:
        planilha.excluir(ABA_USOS_PROJETO, str(por_ass[ass_id]["ID"]))
        eventos.append(_evento(nomes_ass.get(ass_id, ass_id), EV_PROJETO_DESVINCULADO, "Projeto", registro["Nome"], "", momento))
    registrar(eventos)
    planilha.limpar_cache()
    return id_


def excluir_projeto(original: dict):
    atual = _verificar_conflito(ABA_PROJETOS, original)
    usos = planilha.ler_fresco(ABA_USOS_PROJETO)
    vinculados = usos[usos["Projeto ID"].astype(str) == str(atual["ID"])] if not usos.empty else usos
    for _, uso in vinculados.iterrows():
        planilha.excluir(ABA_USOS_PROJETO, str(uso["ID"]))
    planilha.excluir(ABA_PROJETOS, str(atual["ID"]))
    registrar([_evento(atual["Nome"], EV_PROJETO_EXCLUIDO, "Projeto", atual["Nome"], "")])
    planilha.limpar_cache()


def concluir_projeto(original: dict):
    """Conclui o projeto e encerra seus vínculos para retirá-lo dos custos ativos."""
    atual = _verificar_conflito(ABA_PROJETOS, original)
    if normalizar(atual.get("Status")) == "concluído":
        return
    planilha.atualizar_campos(ABA_PROJETOS, str(atual["ID"]), {"Status": "Concluído"})
    usos = planilha.ler_fresco(ABA_USOS_PROJETO)
    vinculados = usos[usos["Projeto ID"].astype(str) == str(atual["ID"])] if not usos.empty else usos
    for _, uso in vinculados.iterrows():
        planilha.atualizar_campos(ABA_USOS_PROJETO, str(uso["ID"]), {"Status": "Concluído"})
    registrar([_evento(atual["Nome"], EV_PROJETO_CONCLUIDO, "Status",
                       atual.get("Status", ""), "Concluído")])
    planilha.limpar_cache()
