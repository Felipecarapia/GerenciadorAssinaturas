"""Regras de projeto, aprovação financeira e projeções derivadas."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
import pandas as pd

from servicos import planilha
from servicos.calculos import juntar_lista, normalizar, para_datahora, separar_lista, vazio
from servicos.cadastros import (
    ErroValidacao, TransicaoInvalida, _evento, _limpar_datas,
    _verificar_conflito, agora, quem, registrar,
)
from servicos.esquema import (
    ABA_ASSINATURAS, ABA_EQUIPE, ABA_FUNCIONARIOS, ABA_PROJETOS, ABA_USOS_PROJETO,
    EQ_APROVADO, EQ_ENCERRADO, EQ_PROPOSTO, EQ_REMOCAO, EQ_VALENDO,
    EV_DESVINCULADO, EV_EQUIPE_PROPOSTA, EV_PROJETO_ALTERADO, EV_PROJETO_ATIVADO,
    EV_PROJETO_CONCLUIDO, EV_PROJETO_CRIADO, EV_PROJETO_EXCLUIDO,
    EV_PROJETO_RECUSADO, EV_PROJETO_SOLICITADO, EV_VINCULADO,
    PERFIL_FINANCEIRO, PROJ_ATIVO, PROJ_CONCLUIDO, PROJ_PENDENTE, PROJ_RECUSADO,
)
from servicos.usuarios import Usuario


def _agora_texto() -> str:
    return agora().strftime("%Y-%m-%d %H:%M:%S")


def _carimbo_posterior(momento: str, anterior: object) -> str:
    """Garante que o carimbo mude, para _verificar_conflito detectar a nova equipe."""
    antes = para_datahora(anterior)
    agora_ = datetime.strptime(momento, "%Y-%m-%d %H:%M:%S")
    if antes is not None and agora_ <= antes:
        agora_ = antes + timedelta(seconds=1)
    return agora_.strftime("%Y-%m-%d %H:%M:%S")


def _projeto_aberto(status: object) -> bool:
    return normalizar(status) != normalizar(PROJ_CONCLUIDO)


def _pares_equipe(equipe: list[dict]) -> set[tuple[str, str]]:
    return {
        (str(membro.get("pessoa_id", "")), str(assinatura_id))
        for membro in equipe
        for assinatura_id in membro.get("assinaturas_ids", [])
    }


def validar_equipe(
    equipe: list[dict], funcionarios: pd.DataFrame | None = None,
    assinaturas: pd.DataFrame | None = None,
) -> dict[str, str]:
    erros: dict[str, str] = {}
    if not equipe:
        return {"Equipe": "Adicione pelo menos uma pessoa ao projeto."}
    funcionarios = planilha.ler_fresco(ABA_FUNCIONARIOS) if funcionarios is None else funcionarios
    assinaturas = planilha.ler_fresco(ABA_ASSINATURAS) if assinaturas is None else assinaturas
    pessoas_validas = set(funcionarios["ID"].astype(str)) if not funcionarios.empty else set()
    assinaturas_validas = {
        str(registro["ID"])
        for _, registro in assinaturas.iterrows()
        if normalizar(registro.get("Status")) in {"ativa", "em teste"}
    }
    pessoas_vistas: set[str] = set()
    for membro in equipe:
        pessoa_id = str(membro.get("pessoa_id", ""))
        ids = {str(valor) for valor in membro.get("assinaturas_ids", []) if str(valor)}
        chave = f"Equipe.{pessoa_id or 'pessoa'}"
        if not pessoa_id or pessoa_id not in pessoas_validas:
            erros[chave] = "A pessoa selecionada não existe mais. Atualize a página."
        elif pessoa_id in pessoas_vistas:
            erros[chave] = "A mesma pessoa não pode aparecer duas vezes no projeto."
        elif not ids:
            erros[chave] = "Escolha pelo menos uma tecnologia para esta pessoa."
        elif not ids <= assinaturas_validas:
            erros[chave] = "Escolha apenas assinaturas com status Ativa ou Em teste."
        pessoas_vistas.add(pessoa_id)
    return erros


def _linhas_projeto(projeto_id: str) -> pd.DataFrame:
    equipe = planilha.ler_fresco(ABA_EQUIPE)
    if equipe.empty:
        return equipe
    return equipe[equipe["Projeto ID"].astype(str) == str(projeto_id)]


def _registro_projeto(dados: dict, atual: dict | None, momento: str) -> dict:
    base = atual or {}
    return {
        "ID": str(base.get("ID", "")),
        "Nome": " ".join(str(dados.get("Nome", "")).split()),
        "Cliente": str(dados.get("Cliente") or "").strip(),
        "Responsável": str(dados.get("Responsável") or "").strip(),
        "Departamento": str(dados.get("Departamento") or "").strip(),
        "Data de início": base.get("Data de início", ""),
        "Data de término": base.get("Data de término", ""),
        "Status": base.get("Status") or PROJ_PENDENTE,
        "Observações": str(dados.get("Observações") or "").strip(),
        "Cadastrado em": base.get("Cadastrado em") or momento,
        "Motivo da recusa": base.get("Motivo da recusa", ""),
        "Solicitado por": base.get("Solicitado por", ""),
        "Solicitado em": base.get("Solicitado em", ""),
        "Aprovado por": base.get("Aprovado por", ""),
        "Aprovado em": base.get("Aprovado em", ""),
        "Recusado por": base.get("Recusado por", ""),
        "Recusado em": base.get("Recusado em", ""),
    }


def _validar_projeto(dados: dict, projetos: pd.DataFrame, id_atual: str | None = None) -> dict[str, str]:
    nome = str(dados.get("Nome", "")).strip()
    if not nome:
        return {"Nome": "Informe o nome do projeto."}
    outros = projetos if id_atual is None else projetos[projetos["ID"].astype(str) != id_atual]
    if not outros.empty and normalizar(nome) in set(outros["Nome"].map(normalizar)):
        return {"Nome": "Já existe um projeto com esse nome."}
    return {}


def salvar_projeto(dados: dict, equipe: list[dict], original: dict | None = None) -> str:
    projetos = planilha.ler_fresco(ABA_PROJETOS)
    erros = _validar_projeto(dados, projetos, str(original["ID"]) if original else None)
    erros.update(validar_equipe(equipe))
    if erros:
        raise ErroValidacao(erros)
    momento = _agora_texto()
    autor = quem()
    desejados = _pares_equipe(equipe)

    if original is None:
        id_ = planilha.novo_id(ABA_PROJETOS)
        registro = _registro_projeto(dados, None, momento)
        registro.update({
            "ID": id_, "Status": PROJ_PENDENTE,
            "Solicitado por": autor, "Solicitado em": momento,
        })
        planilha.inserir(ABA_PROJETOS, [registro])
        novas = [{
            "ID": planilha.novo_id(ABA_EQUIPE), "Projeto ID": id_,
            "Pessoa ID": pessoa_id, "Assinatura ID": assinatura_id,
            "Situação": EQ_PROPOSTO, "Proposto por": autor,
            "Proposto em": momento, "Cadastrado em": momento,
        } for pessoa_id, assinatura_id in sorted(desejados)]
        planilha.inserir(ABA_EQUIPE, novas)
        eventos = [_evento(registro["Nome"], EV_PROJETO_CRIADO, "Projeto", "", registro["Nome"])]
        eventos += [_evento(registro["Nome"], EV_EQUIPE_PROPOSTA, pessoa_id, "", assinatura_id)
                    for pessoa_id, assinatura_id in sorted(desejados)]
    else:
        atual = _verificar_conflito(ABA_PROJETOS, original)
        if normalizar(atual.get("Status")) == normalizar(PROJ_CONCLUIDO):
            raise TransicaoInvalida("Projeto concluído não pode ser editado.")
        id_ = str(atual["ID"])
        registro = _registro_projeto(dados, atual, momento)
        linhas = _linhas_projeto(id_)
        linhas_abertas = linhas[linhas["Situação"].map(normalizar) != normalizar(EQ_ENCERRADO)] if not linhas.empty else linhas
        atuais = {(str(l["Pessoa ID"]), str(l["Assinatura ID"])): l.to_dict() for _, l in linhas_abertas.iterrows()}
        mudou_equipe = desejados != {
            par for par, linha in atuais.items()
            if normalizar(linha.get("Situação")) != normalizar(EQ_REMOCAO)
        }
        for par in desejados:
            linha = atuais.get(par)
            if linha is None:
                planilha.inserir(ABA_EQUIPE, [{
                    "ID": planilha.novo_id(ABA_EQUIPE), "Projeto ID": id_,
                    "Pessoa ID": par[0], "Assinatura ID": par[1], "Situação": EQ_PROPOSTO,
                    "Proposto por": autor, "Proposto em": momento, "Cadastrado em": momento,
                }])
            elif normalizar(linha.get("Situação")) == normalizar(EQ_REMOCAO):
                planilha.atualizar_campos(ABA_EQUIPE, str(linha["ID"]), {"Situação": EQ_APROVADO})
        for par, linha in atuais.items():
            if par in desejados:
                continue
            situacao = normalizar(linha.get("Situação"))
            if situacao == normalizar(EQ_PROPOSTO):
                planilha.excluir(ABA_EQUIPE, str(linha["ID"]))
            elif situacao == normalizar(EQ_APROVADO):
                planilha.atualizar_campos(ABA_EQUIPE, str(linha["ID"]), {
                    "Situação": EQ_REMOCAO, "Proposto por": autor, "Proposto em": momento,
                })
        if mudou_equipe:
            if normalizar(atual.get("Status")) == normalizar(PROJ_ATIVO):
                registro["Status"] = PROJ_PENDENTE
            registro["Solicitado por"] = autor
            registro["Solicitado em"] = _carimbo_posterior(momento, atual.get("Solicitado em"))
        planilha.atualizar(ABA_PROJETOS, id_, _limpar_datas(registro))
        eventos = [_evento(registro["Nome"], EV_PROJETO_ALTERADO, "Projeto", atual.get("Nome", ""), registro["Nome"])]

    registrar(eventos)
    sincronizar_derivados()
    return id_


def solicitar_ativacao(original: dict) -> None:
    atual = _verificar_conflito(ABA_PROJETOS, original)
    if normalizar(atual.get("Status")) != normalizar(PROJ_RECUSADO):
        raise TransicaoInvalida("Somente projetos recusados podem solicitar nova ativação.")
    momento = _agora_texto()
    planilha.atualizar_campos(ABA_PROJETOS, str(atual["ID"]), {
        "Status": PROJ_PENDENTE, "Motivo da recusa": "",
        "Solicitado por": quem(), "Solicitado em": momento,
    })
    registrar([_evento(atual["Nome"], EV_PROJETO_SOLICITADO, "Status", PROJ_RECUSADO, PROJ_PENDENTE)])
    planilha.limpar_cache()


def ativar_projeto(original: dict) -> None:
    atual = _verificar_conflito(ABA_PROJETOS, original)
    if normalizar(atual.get("Status")) != normalizar(PROJ_PENDENTE):
        raise TransicaoInvalida("Somente projetos pendentes podem ser ativados.")
    linhas = _linhas_projeto(str(atual["ID"]))
    abertas = linhas[linhas["Situação"].map(normalizar) != normalizar(EQ_ENCERRADO)] if not linhas.empty else linhas
    equipe_por_pessoa: dict[str, list[str]] = defaultdict(list)
    for _, linha in abertas.iterrows():
        if normalizar(linha.get("Situação")) != normalizar(EQ_REMOCAO):
            equipe_por_pessoa[str(linha["Pessoa ID"])].append(str(linha["Assinatura ID"]))
    erros = validar_equipe([{"pessoa_id": pessoa, "assinaturas_ids": ids} for pessoa, ids in equipe_por_pessoa.items()])
    if erros:
        raise ErroValidacao(erros)
    for _, linha in abertas.iterrows():
        situacao = normalizar(linha.get("Situação"))
        if situacao == normalizar(EQ_PROPOSTO):
            planilha.atualizar_campos(ABA_EQUIPE, str(linha["ID"]), {"Situação": EQ_APROVADO})
        elif situacao == normalizar(EQ_REMOCAO):
            planilha.excluir(ABA_EQUIPE, str(linha["ID"]))
    momento = _agora_texto()
    planilha.atualizar_campos(ABA_PROJETOS, str(atual["ID"]), {
        "Status": PROJ_ATIVO, "Motivo da recusa": "",
        "Aprovado por": quem(), "Aprovado em": momento,
        "Recusado por": "", "Recusado em": "",
    })
    registrar([_evento(atual["Nome"], EV_PROJETO_ATIVADO, "Status", PROJ_PENDENTE, PROJ_ATIVO)])
    sincronizar_derivados()


def recusar_projeto(original: dict, motivo: str) -> None:
    atual = _verificar_conflito(ABA_PROJETOS, original)
    if normalizar(atual.get("Status")) != normalizar(PROJ_PENDENTE):
        raise TransicaoInvalida("Somente projetos pendentes podem ser recusados.")
    motivo_limpo = " ".join(str(motivo).split())
    if len(motivo_limpo) < 10:
        raise ErroValidacao({"motivo": "Informe um motivo com pelo menos 10 caracteres."})
    momento = _agora_texto()
    planilha.atualizar_campos(ABA_PROJETOS, str(atual["ID"]), {
        "Status": PROJ_RECUSADO, "Motivo da recusa": motivo_limpo,
        "Recusado por": quem(), "Recusado em": momento,
    })
    registrar([_evento(atual["Nome"], EV_PROJETO_RECUSADO, "Motivo", "", motivo_limpo)])
    planilha.limpar_cache()


def concluir_projeto(original: dict) -> None:
    atual = _verificar_conflito(ABA_PROJETOS, original)
    if normalizar(atual.get("Status")) == normalizar(PROJ_CONCLUIDO):
        raise TransicaoInvalida("O projeto já está concluído.")
    linhas = _linhas_projeto(str(atual["ID"]))
    for _, linha in linhas.iterrows():
        if normalizar(linha.get("Situação")) == normalizar(EQ_PROPOSTO):
            planilha.excluir(ABA_EQUIPE, str(linha["ID"]))
        else:
            planilha.atualizar_campos(ABA_EQUIPE, str(linha["ID"]), {"Situação": EQ_ENCERRADO})
    planilha.atualizar_campos(ABA_PROJETOS, str(atual["ID"]), {
        "Status": PROJ_CONCLUIDO, "Data de término": agora().date().isoformat(),
    })
    registrar([_evento(atual["Nome"], EV_PROJETO_CONCLUIDO, "Status", atual.get("Status", ""), PROJ_CONCLUIDO)])
    sincronizar_derivados()


def excluir_projeto(original: dict, usuario: Usuario) -> None:
    atual = _verificar_conflito(ABA_PROJETOS, original)
    ja_ativado = not vazio(atual.get("Aprovado em"))
    if ja_ativado and usuario.perfil != PERFIL_FINANCEIRO:
        raise TransicaoInvalida("Somente o Financeiro pode excluir um projeto que já foi ativado.")
    linhas = _linhas_projeto(str(atual["ID"]))
    for _, linha in linhas.iterrows():
        planilha.excluir(ABA_EQUIPE, str(linha["ID"]))
    planilha.excluir(ABA_PROJETOS, str(atual["ID"]))
    registrar([_evento(atual["Nome"], EV_PROJETO_EXCLUIDO, "Projeto", atual["Nome"], "")])
    # Só esvaziar a equipe agora é legítimo; equipe já vazia antes indica migração pendente.
    sincronizar_derivados(permitir_equipe_vazia=not linhas.empty)


def sincronizar_derivados(*, permitir_equipe_vazia: bool = False) -> dict[str, int]:
    projetos = planilha.ler_fresco(ABA_PROJETOS)
    equipe = planilha.ler_fresco(ABA_EQUIPE)
    funcionarios = planilha.ler_fresco(ABA_FUNCIONARIOS)
    assinaturas = planilha.ler_fresco(ABA_ASSINATURAS)
    if equipe.empty and not funcionarios.empty and any(separar_lista(v) for v in funcionarios["Assinaturas"]):
        if not permitir_equipe_vazia:
            raise ErroValidacao({"Migração": "Migração pendente: rode scripts/migrar_equipe.py."})

    nomes_assinaturas = dict(zip(assinaturas["ID"].astype(str), assinaturas["Nome"].astype(str))) if not assinaturas.empty else {}
    projetos_por_id = {str(p["ID"]): p.to_dict() for _, p in projetos.iterrows()}
    assinaturas_por_pessoa: dict[str, set[str]] = defaultdict(set)
    usos_desejados: dict[tuple[str, str], str] = {}
    for _, linha in equipe.iterrows():
        projeto_id = str(linha["Projeto ID"])
        projeto = projetos_por_id.get(projeto_id)
        if not projeto:
            continue
        situacao = str(linha.get("Situação", ""))
        status_projeto = str(projeto.get("Status", ""))
        assinatura_id = str(linha["Assinatura ID"])
        if situacao in EQ_VALENDO and _projeto_aberto(status_projeto):
            nome = nomes_assinaturas.get(assinatura_id)
            if nome:
                assinaturas_por_pessoa[str(linha["Pessoa ID"])].add(nome)
                usos_desejados[(projeto_id, assinatura_id)] = PROJ_ATIVO
        elif normalizar(status_projeto) == normalizar(PROJ_CONCLUIDO) and normalizar(situacao) == normalizar(EQ_ENCERRADO):
            usos_desejados[(projeto_id, assinatura_id)] = PROJ_CONCLUIDO

    alteracoes_func: dict[str, dict] = {}
    eventos = []
    for _, pessoa in funcionarios.iterrows():
        pessoa_id = str(pessoa["ID"])
        antes = set(separar_lista(pessoa.get("Assinaturas")))
        depois = assinaturas_por_pessoa.get(pessoa_id, set())
        if antes == depois:
            continue
        registro = pessoa.to_dict()
        registro = {coluna: registro.get(coluna, "") for coluna in planilha.COLUNAS[ABA_FUNCIONARIOS]}
        registro["Assinaturas"] = juntar_lista(sorted(depois))
        alteracoes_func[pessoa_id] = _limpar_datas(registro)
        eventos += [_evento(nome, EV_VINCULADO, "Usuários", "", pessoa["Nome completo"]) for nome in depois - antes]
        eventos += [_evento(nome, EV_DESVINCULADO, "Usuários", pessoa["Nome completo"], "") for nome in antes - depois]
    planilha.atualizar_varios(ABA_FUNCIONARIOS, alteracoes_func)

    usos = planilha.ler_fresco(ABA_USOS_PROJETO)
    existentes: dict[tuple[str, str], dict] = {}
    duplicados: list[str] = []
    for _, uso in usos.iterrows():
        par = (str(uso["Projeto ID"]), str(uso["Assinatura ID"]))
        if par in existentes:
            duplicados.append(str(uso["ID"]))
        else:
            existentes[par] = uso.to_dict()
    for id_ in duplicados:
        planilha.excluir(ABA_USOS_PROJETO, id_)
    momento = _agora_texto()
    novos = []
    for par, status in usos_desejados.items():
        atual = existentes.get(par)
        projeto = projetos_por_id.get(par[0], {})
        if atual is None:
            novos.append({
                "ID": planilha.novo_id(ABA_USOS_PROJETO), "Projeto ID": par[0],
                "Assinatura ID": par[1], "Finalidade": "",
                "Responsável": projeto.get("Responsável", ""), "Data de início": "",
                "Data de término": "", "Status": status, "Observações": "",
                "Cadastrado em": momento,
            })
        elif str(atual.get("Status")) != status:
            planilha.atualizar_campos(ABA_USOS_PROJETO, str(atual["ID"]), {"Status": status})
    if novos:
        planilha.inserir(ABA_USOS_PROJETO, novos)
    for par, uso in existentes.items():
        if par in usos_desejados:
            continue
        projeto = projetos_por_id.get(par[0])
        if projeto and not _projeto_aberto(projeto.get("Status")):
            # Histórico de projeto concluído sem equipe registrada (ex.: anterior à migração).
            if str(uso.get("Status")) != PROJ_CONCLUIDO:
                planilha.atualizar_campos(ABA_USOS_PROJETO, str(uso["ID"]), {"Status": PROJ_CONCLUIDO})
            continue
        planilha.excluir(ABA_USOS_PROJETO, str(uso["ID"]))
    registrar(eventos)
    planilha.limpar_cache()
    return {"pessoas": len(alteracoes_func), "usos": len(usos_desejados)}
