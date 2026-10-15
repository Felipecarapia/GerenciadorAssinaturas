"""Regras de cálculo: gasto mensal (RF-06), alertas (RF-08) e conversões."""
from datetime import date, datetime

import pandas as pd
import pytest

from servicos import calculos as c

HOJE = date(2026, 10, 15)


@pytest.mark.parametrize("valor, plano, status, esperado", [
    (100, "Mensal", "Ativa", 100),
    (1200, "Anual", "Ativa", 100),
    (300, "Trimestral", "Ativa", 100),
    (600, "Semestral", "Ativa", 100),
    (999, "Vitalício", "Ativa", 0),        # vitalício não entra
    (100, "Mensal", "Cancelada", 0),      # só ativas
    (100, "Mensal", "Pausada", 0),
    (100, "Mensal", "Em teste", 0),
    ("R$ 1.200,00", "anual", "ativa", 100),  # texto e maiúsculas
    ("", "Mensal", "Ativa", 0),
    (-50, "Mensal", "Ativa", 0),
])
def test_custo_mensal(valor, plano, status, esperado):
    assert c.custo_mensal(valor, plano, status) == pytest.approx(esperado)


@pytest.mark.parametrize("texto, esperado", [
    (49.9, 49.9), ("49,90", 49.9), ("R$ 1.234,56", 1234.56), ("1234.56", 1234.56),
    ("1.234.567", 1234567.0), ("abc", None), ("", None), (None, None),
])
def test_para_numero(texto, esperado):
    assert c.para_numero(texto) == (pytest.approx(esperado) if esperado is not None else None)


@pytest.mark.parametrize("v, esperado", [
    ("2026-11-01", date(2026, 11, 1)), ("01/11/2026", date(2026, 11, 1)),
    (46327, date(2026, 11, 1)),  # número de série do Google Sheets
    (datetime(2026, 1, 2, 10), date(2026, 1, 2)), ("31/02/2026", None), ("ontem", None),
])
def test_para_data(v, esperado):
    assert c.para_data(v) == esperado


@pytest.mark.parametrize("dias, nivel", [
    (-5, "vermelho"), (0, "vermelho"), (7, "vermelho"), (8, "amarelo"), (30, "amarelo"),
    (31, "verde"), (None, "nenhum"),
])
def test_nivel_alerta(dias, nivel):
    assert c.nivel_alerta(dias) == nivel


def test_lista_multipla_escolha():
    assert c.separar_lista("Adobe, Figma ,, Slack") == ["Adobe", "Figma", "Slack"]
    assert c.juntar_lista(["Adobe", "Figma", "Adobe", " "]) == "Adobe, Figma"


def test_email_valido():
    assert c.email_valido("ana.souza@empresa.com.br")
    assert not c.email_valido("ana@empresa")
    assert not c.email_valido("ana empresa.com")


def _ass(linhas):
    cols = ["ID", "Nome", "Logo (URL)", "Categoria", "Plano", "Valor (R$)", "Vencimento", "Status", "Cadastrado em"]
    return pd.DataFrame([dict(zip(cols, l)) for l in linhas], columns=cols)


def _func(linhas):
    cols = ["ID", "Nome completo", "E-mail", "Departamento", "Cargo", "Assinaturas", "Cadastrado em"]
    return pd.DataFrame([dict(zip(cols, l)) for l in linhas], columns=cols)


ASS = _ass([
    ("A1", "Figma", "", "Design", "Mensal", 200, "2026-10-20", "Ativa", "2025-01-01"),
    ("A2", "Adobe", "", "Design", "Anual", 2400, "2026-10-10", "Ativa", "2025-01-01"),
    ("A3", "Slack", "", "Comunicação", "Mensal", 300, "2026-12-30", "Cancelada", "2025-01-01"),
    ("A4", "Sublime", "", "Desenvolvimento", "Vitalício", 500, "", "Ativa", "2025-01-01"),
    ("A5", "Zoom", "", "Comunicação", "Mensal", 100, "2026-11-10", "Ativa", "2026-09-10"),
])
FUNC = _func([
    ("F1", "Ana", "ana@x.com", "Marketing", "", "Figma, Adobe", ""),
    ("F2", "Bia", "bia@x.com", "Marketing", "", "Figma", ""),
    ("F3", "Caio", "caio@x.com", "TI", "", "Zoom, Sublime", ""),
])


def test_indicadores():
    p = c.preparar_assinaturas(ASS, HOJE)
    ind = c.indicadores(p, FUNC)
    assert ind["total_ativas"] == 4
    assert ind["gasto_mensal"] == pytest.approx(200 + 200 + 100)  # Adobe 2400/12
    assert ind["gasto_anual"] == pytest.approx(500 * 12)
    assert ind["vencendo_30"] == 2          # Figma (5 dias) e Zoom (26 dias)
    assert ind["vencidas"] == 1             # Adobe
    assert ind["colaboradores"] == 3


def test_cancelada_nao_gera_alerta():
    p = c.preparar_assinaturas(ASS, HOJE)
    slack = p[p["Nome"] == "Slack"].iloc[0]
    assert slack["nivel"] == "nenhum"


def test_alertas_ordenados_por_urgencia():
    p = c.preparar_assinaturas(ASS, HOJE)
    assert c.alertas(p)["Nome"].tolist() == ["Adobe", "Figma", "Zoom"]


def test_custo_por_pessoa_divide_entre_usuarios():
    p = c.preparar_assinaturas(ASS, HOJE)
    cp = c.custo_por_pessoa(p, FUNC).set_index("Nome completo")["Custo mensal"]
    assert cp["Ana"] == pytest.approx(100 + 200)  # metade do Figma + Adobe inteira
    assert cp["Bia"] == pytest.approx(100)
    assert cp["Caio"] == pytest.approx(100)       # Zoom; Sublime é vitalício
    dep = c.gasto_por_departamento(p, FUNC).set_index("Departamento")["Gasto mensal"]
    assert dep["Marketing"] == pytest.approx(400)
    assert dep.sum() == pytest.approx(c.indicadores(p, FUNC)["gasto_mensal"])


def test_top5():
    p = c.preparar_assinaturas(ASS, HOJE)
    assert c.top_mais_caras(p)["Nome"].tolist() == ["Figma", "Adobe", "Zoom"]


def test_evolucao_desfaz_alteracoes_do_historico():
    hist = pd.DataFrame([
        {"Data e hora": "2026-08-15 10:00:00", "Origem": "app", "Quem": "", "Assinatura": "Figma",
         "Evento": "Valor alterado", "Campo": "Valor (R$)", "Valor anterior": "150.00", "Valor novo": "200.00"},
        {"Data e hora": "2026-06-01 10:00:00", "Origem": "planilha", "Quem": "", "Assinatura": "Slack",
         "Evento": "Status alterado", "Campo": "Status", "Valor anterior": "Ativa", "Valor novo": "Cancelada"},
    ])
    ev = c.evolucao_12_meses(ASS, hist, datetime(2026, 10, 15, 12)).set_index("Mês")["Gasto mensal"]
    assert len(ev) == 12
    assert ev["10/2026"] == pytest.approx(500)        # hoje (Zoom já cadastrado)
    assert ev["08/2026"] == pytest.approx(400)        # sem Zoom (cadastrado em 09/2026)
    assert ev["07/2026"] == pytest.approx(150 + 200)  # Figma ainda 150
    assert ev["05/2026"] == pytest.approx(150 + 200 + 300)  # Slack ainda ativa
