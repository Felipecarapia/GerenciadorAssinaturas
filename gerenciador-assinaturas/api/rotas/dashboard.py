from fastapi import APIRouter, Depends

from api.auth import exigir_sessao
from api.base import base, df_json
from servicos import calculos as calc
from servicos.cadastros import agora

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(exigir_sessao)])


@router.get("")
def dashboard():
    dados = base()
    return {
        "indicadores": calc.indicadores(dados.assinaturas, dados.funcionarios),
        "evolucao": df_json(calc.evolucao_12_meses(dados.assinaturas, dados.historico, agora())),
        "categorias": df_json(calc.gasto_por_categoria(dados.assinaturas)),
        "status": df_json(calc.contagem_por_status(dados.assinaturas, dados.listas["Status"])),
        "top": df_json(calc.top_mais_caras(dados.assinaturas)),
        "alertas": df_json(calc.alertas(dados.assinaturas)),
    }
