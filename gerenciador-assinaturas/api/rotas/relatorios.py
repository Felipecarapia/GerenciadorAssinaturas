from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from api.auth import exigir_sessao
from api.base import base, df_json
from servicos import calculos as calc
from servicos import relatorios as rel
from servicos.cadastros import agora

router = APIRouter(prefix="/api/relatorios", tags=["relatorios"], dependencies=[Depends(exigir_sessao)])


def _base_relatorio():
    dados = base()
    momento = agora()
    return dados, rel.Dados(dados.assinaturas, dados.funcionarios, dados.historico, momento), momento


@router.get("/{tipo}/previa")
def previa(tipo: str, dias: int = Query(30, ge=1, le=365)):
    dados, _, _ = _base_relatorio()
    if tipo == "resumo":
        return {"indicadores": calc.indicadores(dados.assinaturas, dados.funcionarios), "categorias": df_json(calc.gasto_por_categoria(dados.assinaturas))}
    if tipo == "categorias":
        df = dados.assinaturas.assign(Categoria=dados.assinaturas["Categoria"].replace("", "Sem categoria"))
        if df.empty:
            return {"itens": []}
        tabela = df.groupby("Categoria", as_index=False).agg(Assinaturas=("ID", "count"), Ativas=("Status", lambda s: int((s == "Ativa").sum())), **{"Gasto mensal": ("mensal", "sum")}).round(2).sort_values("Gasto mensal", ascending=False)
        return {"itens": df_json(tabela)}
    if tipo == "vencimentos":
        return {"itens": df_json(calc.a_vencer(dados.assinaturas, dias)), "dias": dias}
    if tipo == "colaboradores":
        return {"departamentos": df_json(calc.gasto_por_departamento(dados.assinaturas, dados.funcionarios)), "assinaturas": df_json(calc.colaboradores_por_assinatura(dados.assinaturas, dados.funcionarios))}
    raise HTTPException(404, "Relatorio desconhecido.")


@router.get("/{tipo}.{formato}")
def baixar(tipo: str, formato: str, dias: int = Query(30, ge=1, le=365)):
    _, dados, momento = _base_relatorio()
    chave = (tipo, formato.lower())
    geradores = {
        ("resumo", "pdf"): (lambda: rel.resumo_geral_pdf(dados), "application/pdf", "resumo_geral"),
        ("categorias", "xlsx"): (lambda: rel.por_categoria_xlsx(dados), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "assinaturas_por_categoria"),
        ("vencimentos", "pdf"): (lambda: rel.a_vencer_pdf(dados, dias), "application/pdf", f"a_vencer_{dias}_dias"),
        ("colaboradores", "pdf"): (lambda: rel.colaboradores_pdf(dados), "application/pdf", "colaboradores_e_departamentos"),
        ("colaboradores", "xlsx"): (lambda: rel.colaboradores_xlsx(dados), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "colaboradores_e_departamentos"),
    }
    if chave not in geradores:
        raise HTTPException(404, "Formato de relatorio desconhecido.")
    gerar, mime, nome = geradores[chave]
    return Response(gerar(), media_type=mime, headers={"Content-Disposition": f'attachment; filename="{nome}_{momento:%Y-%m-%d}.{formato}"'})
