from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, Response

from api.auth import exigir_sessao
from api.base import base, df_json
from servicos import calculos as calc
from servicos.cadastros import agora
from servicos.esquema import EVENTOS
from servicos.relatorios import tabela_xlsx

router = APIRouter(prefix="/api/historico", tags=["historico"], dependencies=[Depends(exigir_sessao)])


def _dados():
    historico = base().historico.copy()
    if not historico.empty:
        historico["_quando"] = pd.to_datetime(historico["Data e hora"].map(calc.para_datahora), errors="coerce")
        historico = historico.sort_values("_quando", ascending=False)
    return historico


@router.get("")
def listar():
    historico = _dados()
    return {"itens": df_json(historico), "eventos": EVENTOS}


@router.get("/exportar/xlsx")
def exportar():
    historico = _dados().drop(columns=["_quando", "_linha"], errors="ignore")
    conteudo = tabela_xlsx(historico, "Historico")
    nome = f"historico_{agora():%Y-%m-%d}.xlsx"
    return Response(conteudo, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{nome}"'})
