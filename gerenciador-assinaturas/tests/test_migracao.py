from datetime import date

import pytest

from scripts.migrar_equipe import NOME_PROVISORIO, MigracaoRecusada, migrar
from servicos import cadastros, planilha, projetos
from servicos.calculos import separar_lista
from servicos.esquema import ABA_EQUIPE, ABA_FUNCIONARIOS, ABA_HISTORICO, ABA_PROJETOS, ABA_USOS_PROJETO


def _assinatura(nome, valor=100):
    return cadastros.salvar_assinatura({
        "Nome": nome, "Categoria": "Design", "Plano": "Mensal", "Valor (R$)": valor,
        "Vencimento": date(2027, 1, 1), "Status": "Ativa",
    })


def _planilha_antiga():
    """Vínculos no formato anterior: coluna Assinaturas preenchida e Uso por projeto."""
    ana = cadastros.salvar_pessoa({"Nome completo": "Ana", "E-mail": "ana@x.com", "Departamento": "TI"})
    bia = cadastros.salvar_pessoa({"Nome completo": "Bia", "E-mail": "bia@x.com", "Departamento": "TI"})
    figma, slack, miro = _assinatura("Figma"), _assinatura("Slack", 50), _assinatura("Miro", 30)
    planilha.atualizar_campos(ABA_FUNCIONARIOS, ana, {"Assinaturas": "Figma, Slack"})
    planilha.atualizar_campos(ABA_FUNCIONARIOS, bia, {"Assinaturas": "Figma"})
    portal, pausado, antigo = (planilha.novo_id(ABA_PROJETOS) for _ in range(3))
    planilha.inserir(ABA_PROJETOS, [
        {"ID": portal, "Nome": "Portal", "Status": "Ativo"},
        {"ID": pausado, "Nome": "App", "Status": "Pausado"},
        {"ID": antigo, "Nome": "Legado", "Status": "Concluído"},
    ])
    planilha.inserir(ABA_USOS_PROJETO, [
        {"ID": planilha.novo_id(ABA_USOS_PROJETO), "Projeto ID": portal, "Assinatura ID": figma, "Status": "Ativo"},
        {"ID": planilha.novo_id(ABA_USOS_PROJETO), "Projeto ID": portal, "Assinatura ID": miro, "Status": "Ativo"},
        {"ID": planilha.novo_id(ABA_USOS_PROJETO), "Projeto ID": pausado, "Assinatura ID": slack, "Status": "Ativo"},
        {"ID": planilha.novo_id(ABA_USOS_PROJETO), "Projeto ID": antigo, "Assinatura ID": figma, "Status": "Concluído"},
    ])
    planilha.limpar_cache()
    return ana, bia, portal, pausado, antigo


def test_simulacao_nao_grava_e_relata(planilha_vazia):
    _planilha_antiga()
    plano = migrar(aplicar=False)
    assert planilha.ler_fresco(ABA_EQUIPE).empty
    assert plano.provisorios == [("Ana", "Slack")]
    assert plano.usos_sem_pessoa == [("Portal", "Miro")]
    assert plano.assinaturas_sem_projeto == ["Miro"]


def test_aplicar_preserva_assinaturas_e_cria_provisorio(planilha_vazia):
    ana, bia, portal, pausado, antigo = _planilha_antiga()
    migrar(aplicar=True)

    assert separar_lista(planilha.ler_registro(ABA_FUNCIONARIOS, ana)["Assinaturas"]) == ["Figma", "Slack"]
    assert separar_lista(planilha.ler_registro(ABA_FUNCIONARIOS, bia)["Assinaturas"]) == ["Figma"]
    assert planilha.ler_registro(ABA_PROJETOS, portal)["Aprovado por"] == "migração"
    app = planilha.ler_registro(ABA_PROJETOS, pausado)
    assert app["Status"] == "Pendente" and "migrado de Pausado" in app["Observações"]
    assert planilha.ler_registro(ABA_PROJETOS, antigo)["Status"] == "Concluído"

    projetos_df = planilha.ler_fresco(ABA_PROJETOS)
    provisorio = projetos_df[projetos_df["Nome"] == NOME_PROVISORIO].iloc[0]
    assert provisorio["Status"] == "Ativo"
    equipe = planilha.ler_fresco(ABA_EQUIPE)
    linhas = {(l["Projeto ID"], l["Pessoa ID"], l["Situação"]) for _, l in equipe.iterrows()}
    assert (portal, ana, "Aprovado") in linhas and (portal, bia, "Aprovado") in linhas
    assert (pausado, ana, "Proposto") in linhas
    assert (str(provisorio["ID"]), ana, "Aprovado") in linhas
    usos = planilha.ler_fresco(ABA_USOS_PROJETO)
    assert "Concluído" in set(usos[usos["Projeto ID"] == antigo]["Status"])
    assert "Migração para equipes de projeto" in set(planilha.ler_fresco(ABA_HISTORICO)["Evento"])

    with pytest.raises(MigracaoRecusada):
        migrar(aplicar=True)


def test_sincronizar_sem_migracao_e_recusado(planilha_vazia):
    ana, *_ = _planilha_antiga()
    with pytest.raises(cadastros.ErroValidacao) as erro:
        projetos.sincronizar_derivados()
    assert "Migração pendente" in str(erro.value.erros)
    assert planilha.ler_registro(ABA_FUNCIONARIOS, ana)["Assinaturas"] == "Figma, Slack"
