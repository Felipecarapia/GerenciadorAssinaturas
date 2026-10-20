from fastapi import APIRouter, Depends

from api.auth import exigir_sessao
from api.base import base, df_json
from api.modelos import LimparEscolhasIn
from servicos import cadastros, pendencias, planilha
from servicos.esquema import ABA_ASSINATURAS

router = APIRouter(prefix="/api/pendencias", tags=["pendencias"], dependencies=[Depends(exigir_sessao)])


def _listar():
    dados = base()
    bruto = planilha.ler(ABA_ASSINATURAS)
    return dados, pendencias.listar(bruto, dados.funcionarios, dados.listas)


@router.get("")
def listar():
    _, itens = _listar()
    return {"itens": df_json(itens), "total": len(itens)}


@router.post("/pessoas/{id_}/limpar-escolhas")
def limpar_escolhas(id_: str, corpo: LimparEscolhasIn | None = None):
    dados = base()
    nomes = set(corpo.nomes_validos) if corpo and corpo.nomes_validos is not None else set(dados.nomes_assinaturas)
    removidas = cadastros.remover_escolhas_invalidas(id_, nomes)
    return {"removidas": removidas}
