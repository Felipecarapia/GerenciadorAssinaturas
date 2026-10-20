from fastapi import APIRouter, Depends, HTTPException

from api.auth import exigir_sessao
from api.base import base, df_json
from servicos import exemplo, pendencias, planilha
from servicos.cadastros import agora
from servicos.esquema import ABA_ASSINATURAS

router = APIRouter(prefix="/api", tags=["sistema"], dependencies=[Depends(exigir_sessao)])


def _total_pendencias() -> int:
    dados = base()
    bruto = planilha.ler(ABA_ASSINATURAS)
    return len(pendencias.listar(bruto, dados.funcionarios, dados.listas))


@router.get("/base")
def obter_base():
    dados = base()
    return {"assinaturas": df_json(dados.assinaturas), "pessoas": df_json(dados.funcionarios), "projetos": df_json(dados.projetos), "listas": dados.listas, "modo_local": planilha.modo_local()}


@router.get("/listas")
def listas():
    return planilha.listas()


@router.get("/sistema/resumo")
def resumo():
    return {"pendencias": _total_pendencias(), "modo_local": planilha.modo_local()}


@router.post("/sistema/atualizar")
def atualizar():
    planilha.limpar_cache()
    return {"mensagem": "Dados atualizados com a planilha."}


@router.post("/exemplo")
def carregar_exemplo():
    if not planilha.modo_local():
        raise HTTPException(403, "Dados de exemplo so podem ser carregados no modo local.")
    exemplo.carregar(agora(), com_pendencias=True)
    planilha.limpar_cache()
    return {"mensagem": "Dados de exemplo carregados."}
