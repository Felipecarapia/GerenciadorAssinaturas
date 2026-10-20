from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from api.auth import exigir_sessao
from api.base import base, df_json, valor_json
from api.modelos import OriginalIn, ProjetoIn
from servicos import cadastros, calculos as calc, planilha
from servicos.esquema import ABA_PROJETOS

router = APIRouter(prefix="/api/projetos", tags=["projetos"], dependencies=[Depends(exigir_sessao)])


def _payload():
    dados = base()
    custos = calc.custos_por_projeto(dados.assinaturas, dados.projetos, dados.usos_projeto)
    mapa_custos = {str(item["ID"]): item for item in df_json(custos)}
    itens = []
    for projeto in df_json(dados.projetos):
        pid = str(projeto.get("ID", ""))
        projeto.update(mapa_custos.get(pid, {}))
        if not dados.usos_projeto.empty:
            vinculos = dados.usos_projeto[dados.usos_projeto["Projeto ID"].astype(str) == pid]
            projeto["assinaturas_ids"] = vinculos["Assinatura ID"].astype(str).tolist()
        else:
            projeto["assinaturas_ids"] = []
        itens.append(projeto)
    return dados, itens


@router.get("")
def listar():
    dados, itens = _payload()
    total = sum(float(i.get("Custo mensal") or 0) for i in itens)
    ativos = sum(1 for i in itens if calc.normalizar(i.get("Status")) == "ativo")
    return {"itens": itens, "assinaturas": df_json(dados.assinaturas), "listas": dados.listas, "indicadores": {"projetos": len(itens), "ativos": ativos, "custo_mensal": round(total, 2)}}


@router.get("/{id_}")
def obter(id_: str):
    dados, itens = _payload()
    item = next((i for i in itens if str(i.get("ID")) == id_), None)
    if item is None:
        raise HTTPException(404, "Projeto nao encontrado.")
    original = planilha.ler_registro(ABA_PROJETOS, id_)
    return {"item": item, "original": valor_json(original)}


@router.post("", status_code=201)
def criar(corpo: ProjetoIn):
    dados = corpo.dados.model_dump(by_alias=True)
    dados["Responsavel"] = dados.pop("Responsavel", "")
    dados["Observacoes"] = dados.pop("Observacoes", "")
    dados = {"Nome": dados["Nome"], "Cliente": dados["Cliente"], "Responsavel": dados.get("Responsavel", ""), "Departamento": dados["Departamento"], "Status": dados["Status"], "Observacoes": dados.get("Observacoes", "")}
    dados["Responsável"] = dados.pop("Responsavel")
    dados["Observações"] = dados.pop("Observacoes")
    id_ = cadastros.salvar_projeto(dados, corpo.assinaturas_ids)
    return {"id": id_}


@router.put("/{id_}")
def editar(id_: str, corpo: ProjetoIn):
    original = corpo.original or planilha.ler_registro(ABA_PROJETOS, id_)
    if original is None:
        raise HTTPException(404, "Projeto nao encontrado.")
    bruto = corpo.dados.model_dump(by_alias=True)
    dados = {"Nome": bruto["Nome"], "Cliente": bruto["Cliente"], "Responsável": bruto.get("Responsavel", ""), "Departamento": bruto["Departamento"], "Status": bruto["Status"], "Observações": bruto.get("Observacoes", "")}
    id_salvo = cadastros.salvar_projeto(dados, corpo.assinaturas_ids, original)
    return {"id": id_salvo}


@router.post("/{id_}/concluir")
def concluir(id_: str, corpo: OriginalIn | None = None):
    original = corpo.original if corpo and corpo.original else planilha.ler_registro(ABA_PROJETOS, id_)
    if original is None:
        raise HTTPException(404, "Projeto nao encontrado.")
    cadastros.concluir_projeto(original)
    return {"id": id_, "status": "Concluido"}


@router.delete("/{id_}")
def excluir(id_: str, corpo: OriginalIn | None = None):
    original = corpo.original if corpo and corpo.original else planilha.ler_registro(ABA_PROJETOS, id_)
    if original is None:
        raise HTTPException(404, "Projeto nao encontrado.")
    cadastros.excluir_projeto(original)
    return Response(status_code=204)
