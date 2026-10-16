"""Cadastros sobre a planilha local: vínculos, renomear, excluir, conflito e histórico."""
from datetime import date

import pytest

from servicos import cadastros
from servicos.calculos import separar_lista
from servicos.esquema import (
    ABA_ASSINATURAS, ABA_FUNCIONARIOS, ABA_HISTORICO, ABA_PROJETOS, ABA_USOS_PROJETO,
)


def _pessoa(nome, email, assinaturas=()):
    return cadastros.salvar_pessoa(
        {"Nome completo": nome, "E-mail": email, "Departamento": "TI", "Cargo": ""}, list(assinaturas))


def _assinatura(nome, usuarios, valor=100.0, plano="Mensal", status="Ativa", original=None):
    return cadastros.salvar_assinatura(
        {"Nome": nome, "Logo (URL)": "", "Categoria": "Design", "Plano": plano, "Valor (R$)": valor,
         "Vencimento": date(2026, 12, 1), "Status": status}, usuarios, original)


def _assinaturas_de(planilha, id_):
    return separar_lista(planilha.ler_registro(ABA_FUNCIONARIOS, id_)["Assinaturas"])


def test_criar_assinatura_vincula_usuarios(planilha_vazia):
    p = planilha_vazia
    ana, bia = _pessoa("Ana Souza", "ana@empresa.com.br"), _pessoa("Bia Lima", "bia@empresa.com.br")
    _assinatura("Figma", [ana])
    assert _assinaturas_de(p, ana) == ["Figma"]
    assert _assinaturas_de(p, bia) == []
    eventos = p.ler_fresco(ABA_HISTORICO)["Evento"].tolist()
    assert eventos == ["Assinatura criada", "Usuário vinculado"]


def test_validacoes(planilha_vazia):
    ana = _pessoa("Ana Souza", "ana@empresa.com.br")
    _assinatura("Figma", [ana])
    with pytest.raises(cadastros.ErroValidacao) as e:
        _assinatura("figma", [ana])  # nome único (sem diferenciar maiúsculas)
    assert "Nome" in e.value.erros
    with pytest.raises(cadastros.ErroValidacao) as e:
        _assinatura("Adobe, CC", [ana], valor=-1)
    assert {"Nome", "Valor (R$)"} <= set(e.value.erros)
    with pytest.raises(cadastros.ErroValidacao) as e:
        _assinatura("Adobe", [])
    assert "Usuários" in e.value.erros
    with pytest.raises(cadastros.ErroValidacao) as e:
        _pessoa("Outra Ana", "ANA@empresa.com.br")  # e-mail duplicado
    assert "E-mail" in e.value.erros
    with pytest.raises(cadastros.ErroValidacao):
        _pessoa("Sem Email", "nao-e-email")


def test_editar_renomear_e_desvincular(planilha_vazia):
    p = planilha_vazia
    ana, bia = _pessoa("Ana Souza", "ana@empresa.com.br"), _pessoa("Bia Lima", "bia@empresa.com.br")
    id_ = _assinatura("Figma", [ana, bia])
    original = p.ler_registro(ABA_ASSINATURAS, id_)
    _assinatura("Figma Pro", [bia], valor=150.0, plano="Anual", original=original)
    assert _assinaturas_de(p, ana) == []
    assert _assinaturas_de(p, bia) == ["Figma Pro"]  # RF-14: renomeou na pessoa
    hist = p.ler_fresco(ABA_HISTORICO)
    eventos = set(hist["Evento"])
    assert {"Valor alterado", "Plano alterado", "Assinatura renomeada", "Usuário desvinculado"} <= eventos
    valor = hist[hist["Evento"] == "Valor alterado"].iloc[0]
    assert (valor["Valor anterior"], valor["Valor novo"]) == ("100.00", "150.00")


def test_conflito_de_edicao(planilha_vazia):
    """RF-16: alguém mudou a linha na planilha enquanto a janela estava aberta."""
    p = planilha_vazia
    ana = _pessoa("Ana Souza", "ana@empresa.com.br")
    id_ = _assinatura("Figma", [ana])
    aberto = p.ler_registro(ABA_ASSINATURAS, id_)
    # edição direta na planilha (outra pessoa)
    linha = p.numero_da_linha(ABA_ASSINATURAS, id_)
    p.motor().atualizar_celulas(ABA_ASSINATURAS, {f"F{linha}": 999})
    with pytest.raises(cadastros.ConflitoEdicao):
        _assinatura("Figma", [ana], valor=120.0, original=aberto)
    assert p.ler_registro(ABA_ASSINATURAS, id_)["Valor (R$)"] == 999  # não sobrescreveu


def test_excluir_assinatura_remove_das_pessoas(planilha_vazia):
    p = planilha_vazia
    ana = _pessoa("Ana Souza", "ana@empresa.com.br")
    figma = _assinatura("Figma", [ana])
    _assinatura("Slack", [ana])
    cadastros.excluir_assinatura({"ID": figma})
    assert _assinaturas_de(p, ana) == ["Slack"]
    assert p.ler_registro(ABA_ASSINATURAS, figma) is None
    assert "Assinatura excluída" in set(p.ler_fresco(ABA_HISTORICO)["Evento"])


def test_vinculo_pela_tela_da_pessoa(planilha_vazia):
    p = planilha_vazia
    ana = _pessoa("Ana Souza", "ana@empresa.com.br")
    _assinatura("Figma", [ana])
    bia = _pessoa("Bia Lima", "bia@empresa.com.br", ["Figma"])
    from servicos.calculos import usuarios_por_assinatura
    assert set(usuarios_por_assinatura(p.ler_fresco(ABA_FUNCIONARIOS))["Figma"]) == {ana, bia}


def test_ids_gerados_para_linhas_digitadas_na_planilha(planilha_vazia):
    p = planilha_vazia
    p.motor().anexar(ABA_ASSINATURAS, [["", "Notion", "", "Produtividade", "Mensal", 50, "2026-12-01", "Ativa", ""]])
    df = p.ler_fresco(ABA_ASSINATURAS)
    assert df.iloc[0]["ID"].startswith("A-")


def test_pendencias(planilha_vazia):
    from servicos import exemplo, pendencias
    from datetime import datetime
    p = planilha_vazia
    exemplo.carregar(datetime(2026, 10, 15, 10), com_pendencias=True)
    lista = pendencias.listar(p.ler_fresco(ABA_ASSINATURAS), p.ler_fresco(ABA_FUNCIONARIOS), p.listas())
    tipos = set(lista["Tipo"])
    assert {pendencias.T_INEXISTENTE, pendencias.T_EMAIL_DUP, pendencias.T_OBRIGATORIO} <= tipos
    assert (lista["Linha"] >= 2).all()


def test_sem_falso_conflito_sem_alteracao(planilha_vazia):
    p = planilha_vazia
    ana = _pessoa("Ana Souza", "ana@empresa.com.br")
    id_ = _assinatura("Figma", [ana], valor=100.0)
    aberto = p.ler_registro(ABA_ASSINATURAS, id_)
    # Salvando sem alterar nada não deve acusar falso conflito
    salvo_id = cadastros.salvar_assinatura(
        {"Nome": "Figma", "Categoria": "Design", "Plano": "Mensal", "Valor (R$)": 100.0,
         "Vencimento": date(2026, 12, 1), "Status": "Ativa"}, [ana], original=aberto)
    assert salvo_id == id_


def test_registrar_pagamento_avanca_vencimento_e_grava_historico(planilha_vazia):
    from servicos.calculos import para_data
    p = planilha_vazia
    ana = _pessoa("Ana Souza", "ana@empresa.com.br")
    id_ = _assinatura("Figma", [ana], plano="Mensal")
    original = p.ler_registro(ABA_ASSINATURAS, id_)
    assert para_data(original["Vencimento"]) == date(2026, 12, 1)

    novo_venc = cadastros.registrar_pagamento(id_, original)
    assert novo_venc == date(2027, 1, 1)

    # Verifica se atualizou na planilha
    atualizado = p.ler_registro(ABA_ASSINATURAS, id_)
    assert para_data(atualizado["Vencimento"]) == date(2027, 1, 1)

    # Verifica se registrou evento no Histórico
    hist = p.ler_fresco(ABA_HISTORICO)
    ev_pag = hist[hist["Evento"] == "Pagamento registrado"]
    assert not ev_pag.empty
    registro = ev_pag.iloc[0]
    assert registro["Assinatura"] == "Figma"
    assert registro["Campo"] == "Vencimento"
    assert registro["Valor anterior"] == "01/12/2026"
    assert registro["Valor novo"] == "01/01/2027"


def test_registrar_pagamento_conflito_edicao(planilha_vazia):
    p = planilha_vazia
    ana = _pessoa("Ana Souza", "ana@empresa.com.br")
    id_ = _assinatura("Figma", [ana], plano="Mensal")
    original = p.ler_registro(ABA_ASSINATURAS, id_)

    # Outra pessoa altera o plano na planilha enquanto o diálogo estava aberto
    linha = p.numero_da_linha(ABA_ASSINATURAS, id_)
    p.motor().atualizar_celulas(ABA_ASSINATURAS, {f"E{linha}": "Anual"})

    with pytest.raises(cadastros.ConflitoEdicao):
        cadastros.registrar_pagamento(id_, original)


def test_projeto_vincula_assinaturas_e_divide_custos(planilha_vazia):
    from servicos import calculos

    p = planilha_vazia
    ana = _pessoa("Ana Souza", "ana@empresa.com.br")
    assinatura = _assinatura("Claude", [ana], valor=100)
    dados = {"Nome": "Portal", "Cliente": "Cliente A", "Responsável": "Ana",
             "Departamento": "TI", "Data de início": date(2026, 1, 1),
             "Data de término": None, "Status": "Ativo", "Observações": ""}
    p1 = cadastros.salvar_projeto(dados, [assinatura])
    dados["Nome"] = "Aplicativo"
    p2 = cadastros.salvar_projeto(dados, [assinatura])

    projetos = p.ler_fresco(ABA_PROJETOS)
    usos = p.ler_fresco(ABA_USOS_PROJETO)
    ass = calculos.preparar_assinaturas(p.ler_fresco(ABA_ASSINATURAS), date(2026, 1, 1))
    custos = calculos.custos_por_projeto(ass, projetos, usos).set_index("ID")
    assert custos.loc[p1, "Custo mensal"] == 50
    assert custos.loc[p2, "Custo mensal"] == 50
    assert calculos.projetos_por_assinatura(projetos, usos)[assinatura] == ["Aplicativo", "Portal"]

    original = p.ler_registro(ABA_PROJETOS, p2)
    cadastros.excluir_projeto(original)
    assert len(p.ler_fresco(ABA_USOS_PROJETO)) == 1

    original = p.ler_registro(ABA_PROJETOS, p1)
    cadastros.concluir_projeto(original)
    assert p.ler_registro(ABA_PROJETOS, p1)["Status"] == "Concluído"
    assert p.ler_fresco(ABA_USOS_PROJETO).iloc[0]["Status"] == "Concluído"
    projetos = p.ler_fresco(ABA_PROJETOS)
    usos = p.ler_fresco(ABA_USOS_PROJETO)
    custos = calculos.custos_por_projeto(ass, projetos, usos).set_index("ID")
    assert custos.loc[p1, "Custo mensal"] == 0
