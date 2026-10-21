from __future__ import annotations

import io

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Response

from api.auth import exigir_sessao
from api.base import base, df_json, valor_json
from api.modelos import AssinaturaIn, OriginalIn
from servicos import cadastros, calculos as calc, planilha
from servicos.cadastros import agora
from servicos.esquema import ABA_ASSINATURAS
from servicos.esquema import EQ_VALENDO, PROJ_CONCLUIDO
from servicos.relatorios import tabela_xlsx

router = APIRouter(prefix="/api/assinaturas", tags=["assinaturas"], dependencies=[Depends(exigir_sessao)])


def _payload():
    dados = base()
    usuarios = calc.usuarios_por_assinatura(dados.funcionarios)
    projetos = calc.projetos_por_assinatura(dados.projetos, dados.usos_projeto)
    pessoas = {str(p["ID"]): p for p in df_json(dados.funcionarios)}
    projetos_reg = {str(p["ID"]): p for p in df_json(dados.projetos)}
    usada_por: dict[str, list[dict]] = {}
    for linha in df_json(dados.equipe):
        projeto = projetos_reg.get(str(linha.get("Projeto ID", "")), {})
        if linha.get("Situação") not in EQ_VALENDO or calc.normalizar(projeto.get("Status")) == calc.normalizar(PROJ_CONCLUIDO):
            continue
        pessoa = pessoas.get(str(linha.get("Pessoa ID", "")), {})
        usada_por.setdefault(str(linha.get("Assinatura ID", "")), []).append({
            "pessoa_id": str(linha.get("Pessoa ID", "")), "pessoa": pessoa.get("Nome completo", ""),
            "projeto_id": str(linha.get("Projeto ID", "")), "projeto": projeto.get("Nome", ""),
        })
    itens = []
    for registro in df_json(dados.assinaturas):
        registro["usuarios_ids"] = usuarios.get(str(registro.get("Nome", "")), [])
        registro["projetos"] = projetos.get(str(registro.get("ID", "")), [])
        registro["usada_por"] = usada_por.get(str(registro.get("ID", "")), [])
        itens.append(registro)
    return dados, itens


@router.get("")
def listar():
    dados, itens = _payload()
    return {
        "itens": itens,
        "indicadores": calc.indicadores(dados.assinaturas, dados.funcionarios),
        "listas": dados.listas,
        "pessoas": df_json(dados.funcionarios),
    }


@router.get("/{id_}")
def obter(id_: str):
    registro = planilha.ler_registro(ABA_ASSINATURAS, id_)
    if registro is None:
        raise HTTPException(404, "Assinatura nao encontrada.")
    dados = base()
    usuarios = calc.usuarios_por_assinatura(dados.funcionarios)
    return {"item": valor_json(registro), "usuarios_ids": usuarios.get(str(registro.get("Nome", "")), [])}


@router.post("", status_code=201)
def criar(corpo: AssinaturaIn):
    id_ = cadastros.salvar_assinatura(corpo.dados.model_dump(by_alias=True))
    return {"id": id_}


@router.put("/{id_}")
def editar(id_: str, corpo: AssinaturaIn):
    original = corpo.original or planilha.ler_registro(ABA_ASSINATURAS, id_)
    if original is None:
        raise HTTPException(404, "Assinatura nao encontrada.")
    id_salvo = cadastros.salvar_assinatura(corpo.dados.model_dump(by_alias=True), original=original)
    return {"id": id_salvo}


@router.delete("/{id_}")
def excluir(id_: str, corpo: OriginalIn | None = None):
    original = corpo.original if corpo and corpo.original else {"ID": id_}
    cadastros.excluir_assinatura(original)
    return Response(status_code=204)


@router.post("/{id_}/pagamento")
def pagamento(id_: str, corpo: OriginalIn | None = None):
    original = corpo.original if corpo and corpo.original else planilha.ler_registro(ABA_ASSINATURAS, id_)
    novo = cadastros.registrar_pagamento(id_, original)
    return {"vencimento": novo.isoformat()}


@router.get("/{id_}/historico")
def historico(id_: str):
    registro = planilha.ler_registro(ABA_ASSINATURAS, id_)
    if registro is None:
        raise HTTPException(404, "Assinatura nao encontrada.")
    dados = base().historico
    if dados.empty:
        return {"itens": []}
    itens = dados[dados["Assinatura"].astype(str) == str(registro["Nome"])].copy()
    itens["_quando"] = pd.to_datetime(itens["Data e hora"].map(calc.para_datahora), errors="coerce")
    return {"itens": df_json(itens.sort_values("_quando", ascending=False))}


@router.get("/exportar/xlsx", include_in_schema=False)
def exportar():
    dados, itens = _payload()
    if itens:
        tabela = pd.DataFrame(itens)
        tabela = tabela[["Nome", "Categoria", "Plano", "valor_num", "mensal", "venc_data", "Status", "texto_alerta", "usuarios_ids", "projetos"]]
        tabela = tabela.rename(columns={"valor_num": "Valor (R$)", "mensal": "Mensal (R$)", "venc_data": "Vencimento", "texto_alerta": "Alerta", "usuarios_ids": "Usuarios", "projetos": "Projetos"})
        tabela["Usuarios"] = tabela["Usuarios"].map(len)
        tabela["Projetos"] = tabela["Projetos"].map(lambda valor: ", ".join(valor))
    else:
        tabela = pd.DataFrame(columns=["Nome", "Categoria", "Plano", "Valor (R$)", "Mensal (R$)", "Vencimento", "Status", "Alerta", "Usuarios", "Projetos"])
    conteudo = tabela_xlsx(tabela, "Assinaturas", moedas=("Valor (R$)", "Mensal (R$)"), datas=("Vencimento",))
    nome = f"assinaturas_{agora():%Y-%m-%d}.xlsx"
    return Response(conteudo, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{nome}"'})
