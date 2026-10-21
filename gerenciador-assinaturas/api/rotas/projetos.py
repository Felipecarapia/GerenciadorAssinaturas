from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Response

from api.auth import Financeiro, exigir_sessao
from api.base import base, df_json, valor_json
from api.modelos import OriginalIn, ProjetoDados, ProjetoIn, RecusaIn
from servicos import calculos as calc, planilha, projetos as projetos_servico
from servicos.esquema import (
    ABA_PROJETOS, EQ_ENCERRADO, EQ_REMOCAO, PROJ_ATIVO, PROJ_PENDENTE, PROJ_RECUSADO,
)
from servicos.usuarios import Usuario

router = APIRouter(prefix="/api/projetos", tags=["projetos"], dependencies=[Depends(exigir_sessao)])


def _dados_planilha(dados: ProjetoDados) -> dict:
    bruto = dados.model_dump(by_alias=True)
    return {
        "Nome": bruto["Nome"], "Cliente": bruto["Cliente"],
        "Responsável": bruto.get("Responsavel", ""),
        "Departamento": bruto["Departamento"],
        "Observações": bruto.get("Observacoes", ""),
    }


def _equipes(dados) -> dict[str, list[dict]]:
    pessoas = {str(p["ID"]): p for p in df_json(dados.funcionarios)}
    assinaturas = {str(a["ID"]): a for a in df_json(dados.assinaturas)}
    agrupado: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for linha in df_json(dados.equipe):
        if calc.normalizar(linha.get("Situação")) == calc.normalizar(EQ_ENCERRADO):
            continue
        projeto_id, pessoa_id = str(linha.get("Projeto ID", "")), str(linha.get("Pessoa ID", ""))
        assinatura_id = str(linha.get("Assinatura ID", ""))
        agrupado[projeto_id][pessoa_id].append({
            "id": assinatura_id,
            "nome": assinaturas.get(assinatura_id, {}).get("Nome", assinatura_id),
            "situacao": linha.get("Situação", ""),
            "mensal": assinaturas.get(assinatura_id, {}).get("mensal", 0),
        })
    resultado: dict[str, list[dict]] = {}
    for projeto_id, membros in agrupado.items():
        resultado[projeto_id] = [{
            "pessoa_id": pessoa_id,
            "nome": pessoas.get(pessoa_id, {}).get("Nome completo", "Pessoa removida"),
            "email": pessoas.get(pessoa_id, {}).get("E-mail", ""),
            "departamento": pessoas.get(pessoa_id, {}).get("Departamento", ""),
            "assinaturas": tecnologias,
        } for pessoa_id, tecnologias in membros.items()]
    return resultado


def _payload():
    dados = base()
    custos = calc.custos_por_projeto(dados.assinaturas, dados.projetos, dados.usos_projeto)
    mapa_custos = {str(item["ID"]): item for item in df_json(custos)}
    equipes = _equipes(dados)
    itens = []
    for projeto in df_json(dados.projetos):
        projeto_id = str(projeto.get("ID", ""))
        projeto.update(mapa_custos.get(projeto_id, {}))
        projeto["equipe"] = equipes.get(projeto_id, [])
        projeto["Pessoas"] = len(projeto["equipe"])
        projeto["assinaturas_ids"] = sorted({
            tecnologia["id"] for membro in projeto["equipe"]
            for tecnologia in membro["assinaturas"]
            if calc.normalizar(tecnologia["situacao"]) != calc.normalizar(EQ_REMOCAO)
        })
        itens.append(projeto)
    return dados, itens


@router.get("")
def listar():
    dados, itens = _payload()
    contagens = {status: sum(1 for item in itens if calc.normalizar(item.get("Status")) == calc.normalizar(status))
                 for status in (PROJ_PENDENTE, PROJ_RECUSADO, PROJ_ATIVO, "Concluído")}
    return {
        "itens": itens, "assinaturas": df_json(dados.assinaturas),
        "pessoas": df_json(dados.funcionarios), "listas": dados.listas,
        "indicadores": {
            "projetos": len(itens), "ativos": contagens[PROJ_ATIVO],
            "pendentes": contagens[PROJ_PENDENTE], "recusados": contagens[PROJ_RECUSADO],
            "custo_mensal": round(sum(float(i.get("Custo mensal") or 0) for i in itens), 2),
        },
    }


@router.get("/{id_}")
def obter(id_: str):
    _, itens = _payload()
    item = next((i for i in itens if str(i.get("ID")) == id_), None)
    if item is None:
        raise HTTPException(404, "Projeto não encontrado.")
    return {"item": item, "original": valor_json(planilha.ler_registro(ABA_PROJETOS, id_))}


@router.post("", status_code=201)
def criar(corpo: ProjetoIn):
    id_ = projetos_servico.salvar_projeto(
        _dados_planilha(corpo.dados), [membro.model_dump() for membro in corpo.equipe],
    )
    return {"id": id_, "status": PROJ_PENDENTE}


@router.put("/{id_}")
def editar(id_: str, corpo: ProjetoIn):
    original = corpo.original or planilha.ler_registro(ABA_PROJETOS, id_)
    if original is None:
        raise HTTPException(404, "Projeto não encontrado.")
    id_salvo = projetos_servico.salvar_projeto(
        _dados_planilha(corpo.dados), [membro.model_dump() for membro in corpo.equipe], original,
    )
    salvo = planilha.ler_registro(ABA_PROJETOS, id_salvo)
    return {"id": id_salvo, "status": salvo.get("Status") if salvo else ""}


@router.post("/{id_}/solicitar-ativacao")
def solicitar_ativacao(id_: str, corpo: OriginalIn | None = None):
    original = corpo.original if corpo and corpo.original else planilha.ler_registro(ABA_PROJETOS, id_)
    if original is None:
        raise HTTPException(404, "Projeto não encontrado.")
    projetos_servico.solicitar_ativacao(original)
    return {"id": id_, "status": PROJ_PENDENTE}


@router.post("/{id_}/ativar")
def ativar(id_: str, _: Financeiro, corpo: OriginalIn | None = None):
    original = corpo.original if corpo and corpo.original else planilha.ler_registro(ABA_PROJETOS, id_)
    if original is None:
        raise HTTPException(404, "Projeto não encontrado.")
    projetos_servico.ativar_projeto(original)
    return {"id": id_, "status": PROJ_ATIVO}


@router.post("/{id_}/recusar")
def recusar(id_: str, corpo: RecusaIn, _: Financeiro):
    original = corpo.original or planilha.ler_registro(ABA_PROJETOS, id_)
    if original is None:
        raise HTTPException(404, "Projeto não encontrado.")
    projetos_servico.recusar_projeto(original, corpo.motivo)
    return {"id": id_, "status": PROJ_RECUSADO}


@router.post("/{id_}/concluir")
def concluir(id_: str, corpo: OriginalIn | None = None):
    original = corpo.original if corpo and corpo.original else planilha.ler_registro(ABA_PROJETOS, id_)
    if original is None:
        raise HTTPException(404, "Projeto não encontrado.")
    projetos_servico.concluir_projeto(original)
    return {"id": id_, "status": "Concluído"}


@router.delete("/{id_}")
def excluir(id_: str, usuario: Usuario = Depends(exigir_sessao), corpo: OriginalIn | None = None):
    original = corpo.original if corpo and corpo.original else planilha.ler_registro(ABA_PROJETOS, id_)
    if original is None:
        raise HTTPException(404, "Projeto não encontrado.")
    projetos_servico.excluir_projeto(original, usuario)
    return Response(status_code=204)
