from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Response

from api.auth import exigir_sessao
from api.base import base, df_json, valor_json
from api.modelos import PessoaIn
from servicos import cadastros, calculos as calc, planilha
from servicos.cadastros import agora
from servicos.esquema import ABA_FUNCIONARIOS
from servicos.relatorios import tabela_xlsx

router = APIRouter(prefix="/api/pessoas", tags=["pessoas"], dependencies=[Depends(exigir_sessao)])


def _itens():
    dados = base()
    custos = calc.custo_por_pessoa(dados.assinaturas, dados.funcionarios)
    if custos.empty:
        return dados, []
    tabela = custos.merge(dados.funcionarios[["ID", "Assinaturas"]], on="ID", how="left")
    tabela["assinaturas_lista"] = tabela["Assinaturas"].map(calc.separar_lista)
    return dados, df_json(tabela.sort_values("Nome completo"))


@router.get("")
def listar():
    dados, itens = _itens()
    departamentos = len({str(i.get("Departamento", "")) for i in itens if i.get("Departamento")})
    media = sum(float(i.get("Custo mensal") or 0) for i in itens) / len(itens) if itens else 0
    return {"itens": itens, "listas": dados.listas, "assinaturas": df_json(dados.assinaturas), "indicadores": {"colaboradores": len(itens), "departamentos": departamentos, "custo_medio": round(media, 2)}}


@router.get("/{id_}")
def obter(id_: str):
    registro = planilha.ler_registro(ABA_FUNCIONARIOS, id_)
    if registro is None:
        raise HTTPException(404, "Pessoa nao encontrada.")
    dados = base()
    detalhe = calc.detalhe_pessoa(dados.assinaturas, dados.funcionarios, id_)
    return {"item": valor_json(registro), "detalhe": df_json(detalhe), "assinaturas": calc.separar_lista(registro.get("Assinaturas"))}


@router.post("", status_code=201)
def criar(corpo: PessoaIn):
    id_ = cadastros.salvar_pessoa(corpo.dados.model_dump(by_alias=True), corpo.assinaturas)
    return {"id": id_}


@router.put("/{id_}")
def editar(id_: str, corpo: PessoaIn):
    original = corpo.original or planilha.ler_registro(ABA_FUNCIONARIOS, id_)
    if original is None:
        raise HTTPException(404, "Pessoa nao encontrada.")
    id_salvo = cadastros.salvar_pessoa(corpo.dados.model_dump(by_alias=True), corpo.assinaturas, original)
    return {"id": id_salvo}


@router.delete("/{id_}")
def excluir(id_: str):
    cadastros.excluir_pessoa({"ID": id_})
    return Response(status_code=204)


@router.get("/exportar/xlsx", include_in_schema=False)
def exportar():
    _, itens = _itens()
    tabela = pd.DataFrame(itens)
    if not tabela.empty:
        tabela = tabela.drop(columns=["ID", "_linha", "assinaturas_lista"], errors="ignore")
    conteudo = tabela_xlsx(tabela, "Pessoas", moedas=("Custo mensal",))
    nome = f"pessoas_{agora():%Y-%m-%d}.xlsx"
    return Response(conteudo, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{nome}"'})
