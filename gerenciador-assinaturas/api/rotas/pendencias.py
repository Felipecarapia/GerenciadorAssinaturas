from fastapi import APIRouter, Depends

from api.auth import exigir_sessao
from api.base import base, df_json
from servicos import pendencias, planilha, projetos
from servicos.esquema import ABA_ASSINATURAS

router = APIRouter(prefix="/api/pendencias", tags=["pendencias"], dependencies=[Depends(exigir_sessao)])


def _listar():
    dados = base()
    bruto = planilha.ler(ABA_ASSINATURAS)
    return dados, pendencias.listar(bruto, dados.funcionarios, dados.listas, dados.projetos, dados.equipe)


@router.get("")
def listar():
    _, itens = _listar()
    return {"itens": df_json(itens), "total": len(itens)}


@router.post("/recalcular")
def recalcular():
    return {"alteradas": projetos.sincronizar_derivados()}
