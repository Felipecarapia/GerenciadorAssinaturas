from datetime import date

import pytest

from servicos import cadastros, calculos as calc, planilha, projetos
from servicos.cadastros import ConflitoEdicao, ErroValidacao
from servicos.esquema import (
    ABA_ASSINATURAS, ABA_EQUIPE, ABA_FUNCIONARIOS, ABA_HISTORICO, ABA_PROJETOS, ABA_USOS_PROJETO,
)


def _pessoa(nome="Ana Souza", email="ana@empresa.com.br"):
    return cadastros.salvar_pessoa({"Nome completo": nome, "E-mail": email, "Departamento": "TI", "Cargo": ""})


def _assinatura(nome="Figma", valor=120):
    return cadastros.salvar_assinatura({
        "Nome": nome, "Logo (URL)": "", "Categoria": "Design", "Plano": "Mensal",
        "Valor (R$)": valor, "Vencimento": date(2027, 1, 10), "Status": "Ativa",
    })


def _projeto(equipe, nome="Portal"):
    return projetos.salvar_projeto({"Nome": nome}, equipe)


def _registro(projeto_id):
    return planilha.ler_registro(ABA_PROJETOS, projeto_id)


def _assinaturas_de(pessoa_id):
    return calc.separar_lista(planilha.ler_registro(ABA_FUNCIONARIOS, pessoa_id)["Assinaturas"])


def _situacoes(projeto_id):
    equipe = planilha.ler_fresco(ABA_EQUIPE)
    return sorted(equipe[equipe["Projeto ID"].astype(str) == projeto_id]["Situação"])


def _ativo(equipe, nome="Portal"):
    projeto_id = _projeto(equipe, nome)
    projetos.ativar_projeto(_registro(projeto_id))
    return projeto_id


def test_criar_nasce_pendente_e_nao_libera_acesso(planilha_vazia):
    ana, figma = _pessoa(), _assinatura()
    projeto_id = _projeto([{"pessoa_id": ana, "assinaturas_ids": [figma]}])
    assert _registro(projeto_id)["Status"] == "Pendente"
    assert _situacoes(projeto_id) == ["Proposto"]
    assert _assinaturas_de(ana) == []


def test_ativar_aprova_linhas_e_preenche_derivados(planilha_vazia):
    ana, figma = _pessoa(), _assinatura()
    projeto_id = _ativo([{"pessoa_id": ana, "assinaturas_ids": [figma]}])
    assert _registro(projeto_id)["Status"] == "Ativo"
    assert _registro(projeto_id)["Aprovado em"]
    assert _situacoes(projeto_id) == ["Aprovado"]
    assert _assinaturas_de(ana) == ["Figma"]
    usos = planilha.ler_fresco(ABA_USOS_PROJETO)
    assert list(zip(usos["Projeto ID"], usos["Assinatura ID"], usos["Status"])) == [(projeto_id, figma, "Ativo")]
    eventos = set(planilha.ler_fresco(ABA_HISTORICO)["Evento"])
    assert {"Projeto ativado", "Usuário vinculado"} <= eventos


def test_recusar_exige_motivo_e_grava(planilha_vazia):
    ana, figma = _pessoa(), _assinatura()
    projeto_id = _projeto([{"pessoa_id": ana, "assinaturas_ids": [figma]}])
    with pytest.raises(ErroValidacao):
        projetos.recusar_projeto(_registro(projeto_id), "curto")
    projetos.recusar_projeto(_registro(projeto_id), "Escopo e custo precisam de revisão")
    registro = _registro(projeto_id)
    assert registro["Status"] == "Recusado"
    assert registro["Motivo da recusa"] == "Escopo e custo precisam de revisão"
    assert registro["Recusado em"]


def test_recusado_editar_e_solicitar_volta_para_pendente(planilha_vazia):
    ana, bia, figma = _pessoa(), _pessoa("Bia Lima", "bia@empresa.com.br"), _assinatura()
    projeto_id = _projeto([{"pessoa_id": ana, "assinaturas_ids": [figma]}])
    projetos.recusar_projeto(_registro(projeto_id), "Falta a pessoa de design")
    projetos.salvar_projeto({"Nome": "Portal"}, [
        {"pessoa_id": ana, "assinaturas_ids": [figma]}, {"pessoa_id": bia, "assinaturas_ids": [figma]},
    ], _registro(projeto_id))
    assert _registro(projeto_id)["Status"] == "Recusado"
    assert _registro(projeto_id)["Motivo da recusa"]
    projetos.solicitar_ativacao(_registro(projeto_id))
    assert _registro(projeto_id)["Status"] == "Pendente"
    assert _registro(projeto_id)["Motivo da recusa"] == ""


def test_ativo_adicionar_tecnologia_volta_pendente_sem_liberar(planilha_vazia):
    ana, figma, slack = _pessoa(), _assinatura(), _assinatura("Slack", 50)
    projeto_id = _ativo([{"pessoa_id": ana, "assinaturas_ids": [figma]}])
    projetos.salvar_projeto({"Nome": "Portal"}, [{"pessoa_id": ana, "assinaturas_ids": [figma, slack]}], _registro(projeto_id))
    assert _registro(projeto_id)["Status"] == "Pendente"
    assert _situacoes(projeto_id) == ["Aprovado", "Proposto"]
    assert _assinaturas_de(ana) == ["Figma"]


def test_ativo_editar_so_descricao_continua_ativo(planilha_vazia):
    ana, figma = _pessoa(), _assinatura()
    projeto_id = _ativo([{"pessoa_id": ana, "assinaturas_ids": [figma]}])
    projetos.salvar_projeto({"Nome": "Portal 2", "Cliente": "IRT"}, [{"pessoa_id": ana, "assinaturas_ids": [figma]}], _registro(projeto_id))
    assert _registro(projeto_id)["Status"] == "Ativo"
    assert _registro(projeto_id)["Nome"] == "Portal 2"


def test_ativo_remover_pessoa_so_perde_acesso_depois_de_ativar(planilha_vazia):
    ana, bia, figma = _pessoa(), _pessoa("Bia Lima", "bia@empresa.com.br"), _assinatura()
    projeto_id = _ativo([{"pessoa_id": ana, "assinaturas_ids": [figma]}, {"pessoa_id": bia, "assinaturas_ids": [figma]}])
    projetos.salvar_projeto({"Nome": "Portal"}, [{"pessoa_id": ana, "assinaturas_ids": [figma]}], _registro(projeto_id))
    assert _situacoes(projeto_id) == ["Aprovado", "Remoção proposta"]
    assert _assinaturas_de(bia) == ["Figma"]
    projetos.ativar_projeto(_registro(projeto_id))
    assert _situacoes(projeto_id) == ["Aprovado"]
    assert _assinaturas_de(bia) == []
    assert _assinaturas_de(ana) == ["Figma"]


def test_desfazer_remocao_volta_para_aprovado(planilha_vazia):
    ana, bia, figma = _pessoa(), _pessoa("Bia Lima", "bia@empresa.com.br"), _assinatura()
    equipe = [{"pessoa_id": ana, "assinaturas_ids": [figma]}, {"pessoa_id": bia, "assinaturas_ids": [figma]}]
    projeto_id = _ativo(equipe)
    projetos.salvar_projeto({"Nome": "Portal"}, equipe[:1], _registro(projeto_id))
    projetos.salvar_projeto({"Nome": "Portal"}, equipe, _registro(projeto_id))
    assert _situacoes(projeto_id) == ["Aprovado", "Aprovado"]


def test_mesma_tecnologia_em_dois_projetos_conta_uma_vez(planilha_vazia):
    ana, bia, figma = _pessoa(), _pessoa("Bia Lima", "bia@empresa.com.br"), _assinatura(valor=120)
    _ativo([{"pessoa_id": ana, "assinaturas_ids": [figma]}], "Portal")
    _ativo([{"pessoa_id": ana, "assinaturas_ids": [figma]}, {"pessoa_id": bia, "assinaturas_ids": [figma]}], "App")
    assert _assinaturas_de(ana) == ["Figma"]
    preparadas = calc.preparar_assinaturas(planilha.ler_fresco(ABA_ASSINATURAS), date(2026, 10, 21))
    custos = calc.custo_por_pessoa(preparadas, planilha.ler_fresco(ABA_FUNCIONARIOS))
    assert custos.set_index("ID").loc[ana, "Custo mensal"] == 60


def test_ativar_com_original_desatualizado_da_conflito(planilha_vazia):
    ana, bia, figma = _pessoa(), _pessoa("Bia Lima", "bia@empresa.com.br"), _assinatura()
    projeto_id = _projeto([{"pessoa_id": ana, "assinaturas_ids": [figma]}])
    visto_pelo_financeiro = _registro(projeto_id)
    projetos.salvar_projeto({"Nome": "Portal"}, [
        {"pessoa_id": ana, "assinaturas_ids": [figma]}, {"pessoa_id": bia, "assinaturas_ids": [figma]},
    ], _registro(projeto_id))
    with pytest.raises(ConflitoEdicao):
        projetos.ativar_projeto(visto_pelo_financeiro)
    assert _registro(projeto_id)["Status"] == "Pendente"


def test_ativar_com_assinatura_cancelada_no_caminho(planilha_vazia):
    ana, figma = _pessoa(), _assinatura()
    projeto_id = _projeto([{"pessoa_id": ana, "assinaturas_ids": [figma]}])
    original = planilha.ler_registro(ABA_ASSINATURAS, figma)
    cadastros.salvar_assinatura({
        "Nome": "Figma", "Categoria": "Design", "Plano": "Mensal", "Valor (R$)": 120,
        "Vencimento": date(2027, 1, 10), "Status": "Cancelada",
    }, original=original)
    with pytest.raises(ErroValidacao):
        projetos.ativar_projeto(_registro(projeto_id))
    assert _registro(projeto_id)["Status"] == "Pendente"


def test_concluir_encerra_e_tira_das_pessoas(planilha_vazia):
    ana, figma = _pessoa(), _assinatura()
    projeto_id = _ativo([{"pessoa_id": ana, "assinaturas_ids": [figma]}])
    projetos.concluir_projeto(_registro(projeto_id))
    assert _registro(projeto_id)["Status"] == "Concluído"
    assert _situacoes(projeto_id) == ["Encerrado"]
    assert _assinaturas_de(ana) == []
    assert list(planilha.ler_fresco(ABA_USOS_PROJETO)["Status"]) == ["Concluído"]


def test_validacoes_da_equipe(planilha_vazia):
    ana, figma = _pessoa(), _assinatura()
    with pytest.raises(ErroValidacao) as vazia:
        _projeto([])
    assert "Equipe" in vazia.value.erros
    with pytest.raises(ErroValidacao) as repetida:
        _projeto([{"pessoa_id": ana, "assinaturas_ids": [figma]}, {"pessoa_id": ana, "assinaturas_ids": [figma]}])
    assert f"Equipe.{ana}" in repetida.value.erros
    with pytest.raises(ErroValidacao):
        _projeto([{"pessoa_id": ana, "assinaturas_ids": []}])


def test_renomear_assinatura_atualiza_pessoas(planilha_vazia):
    ana, figma = _pessoa(), _assinatura()
    _ativo([{"pessoa_id": ana, "assinaturas_ids": [figma]}])
    cadastros.salvar_assinatura({
        "Nome": "Figma Pro", "Categoria": "Design", "Plano": "Mensal", "Valor (R$)": 120,
        "Vencimento": date(2027, 1, 10), "Status": "Ativa",
    }, original=planilha.ler_registro(ABA_ASSINATURAS, figma))
    assert _assinaturas_de(ana) == ["Figma Pro"]


def test_editar_pessoa_preserva_assinaturas(planilha_vazia):
    ana, figma = _pessoa(), _assinatura()
    _ativo([{"pessoa_id": ana, "assinaturas_ids": [figma]}])
    cadastros.salvar_pessoa({"Nome completo": "Ana Souza Lima", "E-mail": "ana@empresa.com.br", "Departamento": "TI", "Cargo": "Líder"},
                            original=planilha.ler_registro(ABA_FUNCIONARIOS, ana))
    assert _assinaturas_de(ana) == ["Figma"]


def test_exclusoes_listam_os_projetos(planilha_vazia):
    ana, figma = _pessoa(), _assinatura()
    _projeto([{"pessoa_id": ana, "assinaturas_ids": [figma]}], "Portal Aberto")
    with pytest.raises(ErroValidacao) as pessoa:
        cadastros.excluir_pessoa({"ID": ana})
    assert "Portal Aberto" in pessoa.value.erros["Pessoa"]
    with pytest.raises(ErroValidacao) as assinatura:
        cadastros.excluir_assinatura({"ID": figma})
    assert "Portal Aberto" in assinatura.value.erros["Assinatura"]
