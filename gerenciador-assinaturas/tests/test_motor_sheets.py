"""O motor do Google Sheets contra uma planilha falsa em memória (sem rede).

Confere o que o app manda para a API: modo RAW, datas como número de série,
linhas localizadas pelo ID e números de série lidos de volta corretamente.
"""
import re
from datetime import date

import pytest

from servicos import cadastros, planilha
from servicos.calculos import para_data, separar_lista
from servicos.esquema import ABA_ASSINATURAS, ABA_FUNCIONARIOS, ABA_HISTORICO, COLUNAS, LISTAS_PADRAO


class AbaFalsa:
    def __init__(self, cabecalho):
        self.linhas = [list(cabecalho)]
        self.opcoes = set()

    def get_all_values(self, value_render_option=None):
        assert value_render_option == "UNFORMATTED_VALUE"
        return [list(l) for l in self.linhas]

    def append_rows(self, valores, value_input_option, table_range, insert_data_option):
        self.opcoes.add(value_input_option)
        self.linhas += [list(v) for v in valores]

    def batch_update(self, dados, value_input_option):
        self.opcoes.add(value_input_option)
        for d in dados:
            m = re.fullmatch(r"([A-Z]+)(\d+)", d["range"])
            col, lin = ord(m.group(1)) - 65, int(m.group(2)) - 1
            while len(self.linhas) <= lin:
                self.linhas.append([])
            linha = self.linhas[lin]
            for j, v in enumerate(d["values"][0]):
                while len(linha) <= col + j:
                    linha.append("")
                linha[col + j] = v

    def delete_rows(self, n):
        del self.linhas[n - 1]


class PlanilhaFalsa:
    def __init__(self):
        self.abas = {nome: AbaFalsa(cols) for nome, cols in COLUNAS.items()}
        lis = self.abas["Listas"]
        for i in range(9):
            lis.linhas.append([LISTAS_PADRAO[c][i] if i < len(LISTAS_PADRAO[c]) else "" for c in COLUNAS["Listas"]])

    def worksheet(self, nome):
        return self.abas[nome]


@pytest.fixture
def sheets(monkeypatch):
    motor = planilha.MotorGoogleSheets.__new__(planilha.MotorGoogleSheets)
    motor._planilha, motor._abas = PlanilhaFalsa(), {}
    monkeypatch.setattr(planilha, "motor", lambda: motor)
    planilha.limpar_cache()
    yield motor._planilha
    planilha.limpar_cache()


def test_fluxo_completo_no_sheets(sheets):
    ana = cadastros.salvar_pessoa({"Nome completo": "Ana", "E-mail": "ana@x.com.br", "Departamento": "TI"}, [])
    id_ = cadastros.salvar_assinatura(
        {"Nome": "Figma", "Categoria": "Design", "Plano": "Mensal", "Valor (R$)": 150.0,
         "Vencimento": date(2026, 11, 1), "Status": "Ativa"}, [ana])

    ass = sheets.abas[ABA_ASSINATURAS].linhas[1]
    assert ass[COLUNAS[ABA_ASSINATURAS].index("Vencimento")] == 46327  # número de série
    assert ass[COLUNAS[ABA_ASSINATURAS].index("Valor (R$)")] == 150.0
    assert all(o == "RAW" for a in sheets.abas.values() for o in a.opcoes)

    # edição direta na planilha não muda a posição: ordenar/inserir linha acima
    sheets.abas[ABA_ASSINATURAS].linhas.insert(1, ["", "Slack", "", "Comunicação", "Mensal", 90, 46400, "Ativa", ""])
    original = planilha.ler_registro(ABA_ASSINATURAS, id_)
    assert para_data(original["Vencimento"]) == date(2026, 11, 1)
    cadastros.salvar_assinatura(
        {"Nome": "Figma", "Categoria": "Design", "Plano": "Mensal", "Valor (R$)": 175.5,
         "Vencimento": date(2026, 12, 1), "Status": "Ativa"}, [ana], original)
    figma = [l for l in sheets.abas[ABA_ASSINATURAS].linhas if l[1] == "Figma"][0]
    assert figma[5] == 175.5
    assert isinstance(figma[8], (int, float))  # Cadastrado em continua data
    slack = [l for l in sheets.abas[ABA_ASSINATURAS].linhas if l[1] == "Slack"][0]
    assert slack[0].startswith("A-")  # ID gerado para a linha digitada à mão

    hist = planilha.ler_fresco(ABA_HISTORICO)
    valor = hist[hist["Evento"] == "Valor alterado"].iloc[0]
    assert (valor["Valor anterior"], valor["Valor novo"]) == ("150.00", "175.50")  # texto, sem reinterpretar

    cadastros.excluir_assinatura({"ID": id_})
    func = planilha.ler_fresco(ABA_FUNCIONARIOS).iloc[0]
    assert separar_lista(func["Assinaturas"]) == []
