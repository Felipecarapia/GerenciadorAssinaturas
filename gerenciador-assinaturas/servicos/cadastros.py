"""Operações de cadastro: validação, vínculos nos dois sentidos, histórico
e proteção contra edição simultânea (RF-12 a RF-16, RF-18 a RF-23)."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import streamlit as st

from servicos import planilha
from servicos.calculos import (
    email_valido, formatar_reais, juntar_lista, normalizar, para_data, para_numero, separar_lista, vazio,
)
from servicos.esquema import (
    ABA_ASSINATURAS, ABA_FUNCIONARIOS, ABA_HISTORICO, COLUNAS, EV_CRIADA,
    EV_DESVINCULADO, EV_EXCLUIDA, EV_VINCULADO, EVENTO_POR_CAMPO,
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
    planilha.excluir(ABA_ASSINATURAS, original["ID"])
    eventos.append(_evento(nome, EV_EXCLUIDA, "", nome, "", momento))
    registrar(eventos)
    planilha.limpar_cache()


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
