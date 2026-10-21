from datetime import date
import pytest

from servicos import cadastros, planilha, projetos
from servicos.esquema import ABA_ASSINATURAS, ABA_EQUIPE, ABA_FUNCIONARIOS, ABA_PROJETOS
from servicos.usuarios import Usuario


def _pessoa(nome="Ana Souza", email="ana@empresa.com.br"):
    return cadastros.salvar_pessoa({"Nome completo": nome, "E-mail": email, "Departamento": "TI", "Cargo": ""})


def _assinatura(nome="Figma"):
    return cadastros.salvar_assinatura({"Nome": nome, "Logo (URL)": "", "Categoria": "Design", "Plano": "Mensal", "Valor (R$)": 120, "Vencimento": date(2027, 1, 10), "Status": "Ativa"})


def test_assinatura_e_pessoa_nao_recebem_vinculos_diretos(planilha_vazia):
    pessoa = _pessoa()
    assinatura = _assinatura()
    assert planilha.ler_registro(ABA_FUNCIONARIOS, pessoa)["Assinaturas"] == ""
    assert planilha.ler_registro(ABA_ASSINATURAS, assinatura)["Nome"] == "Figma"


def test_validacoes_basicas(planilha_vazia):
    _pessoa()
    with pytest.raises(cadastros.ErroValidacao):
        _pessoa("Outra", "ana@empresa.com.br")
    _assinatura()
    with pytest.raises(cadastros.ErroValidacao):
        _assinatura("figma")


def test_bloqueia_exclusao_em_projeto_aberto(planilha_vazia):
    pessoa, assinatura = _pessoa(), _assinatura()
    projeto_id = projetos.salvar_projeto({"Nome": "Portal"}, [{"pessoa_id": pessoa, "assinaturas_ids": [assinatura]}])
    with pytest.raises(cadastros.ErroValidacao):
        cadastros.excluir_pessoa({"ID": pessoa})
    with pytest.raises(cadastros.ErroValidacao):
        cadastros.excluir_assinatura({"ID": assinatura})
    assert planilha.ler_registro(ABA_PROJETOS, projeto_id) is not None


def test_recusa_exige_motivo_e_conclusao_nao_reabre(planilha_vazia):
    pessoa, assinatura = _pessoa(), _assinatura()
    projeto_id = projetos.salvar_projeto({"Nome": "Portal"}, [{"pessoa_id": pessoa, "assinaturas_ids": [assinatura]}])
    original = planilha.ler_registro(ABA_PROJETOS, projeto_id)
    with pytest.raises(cadastros.ErroValidacao):
        projetos.recusar_projeto(original, "curto")
    projetos.ativar_projeto(original)
    projetos.concluir_projeto(planilha.ler_registro(ABA_PROJETOS, projeto_id))
    assert set(planilha.ler_fresco(ABA_EQUIPE)["Situação"]) == {"Encerrado"}
    with pytest.raises(cadastros.TransicaoInvalida):
        projetos.salvar_projeto({"Nome": "Portal"}, [{"pessoa_id": pessoa, "assinaturas_ids": [assinatura]}], planilha.ler_registro(ABA_PROJETOS, projeto_id))


def test_exclusao_de_projeto_ativado_so_financeiro(planilha_vazia):
    pessoa, assinatura = _pessoa(), _assinatura()
    projeto_id = projetos.salvar_projeto({"Nome": "Portal"}, [{"pessoa_id": pessoa, "assinaturas_ids": [assinatura]}])
    projetos.ativar_projeto(planilha.ler_registro(ABA_PROJETOS, projeto_id))
    atual = planilha.ler_registro(ABA_PROJETOS, projeto_id)
    with pytest.raises(cadastros.TransicaoInvalida):
        projetos.excluir_projeto(atual, Usuario("U", "Suporte", "s@x.com", "suporte"))
    projetos.excluir_projeto(atual, Usuario("U", "Financeiro", "f@x.com", "financeiro"))
    assert planilha.ler_registro(ABA_PROJETOS, projeto_id) is None
