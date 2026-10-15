"""Prepara a planilha do Google com as 4 abas, listas suspensas, validações e proteções.

Uso (na pasta do projeto, com .streamlit/secrets.toml preenchido):

    python scripts/criar_planilha_modelo.py
    python scripts/criar_planilha_modelo.py --so-aviso   # Histórico só com aviso, sem bloqueio

Pode rodar numa planilha nova (vazia) ou existente: abas que já existem são
mantidas e só recebem cabeçalho, validações e formatos. Nenhum dado é apagado.

Passo manual depois (o Google não permite fazer pela API):
  Na aba Funcionários, selecione a coluna Assinaturas > Dados > Validação de
  dados > clique na regra > marque "Permitir seleções múltiplas" > Concluído.
"""
from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from servicos.esquema import (  # noqa: E402
    ABA_ASSINATURAS, ABA_FUNCIONARIOS, ABA_HISTORICO, ABA_LISTAS, COLUNAS, LISTAS_PADRAO,
)


def carregar_segredos():
    caminho = RAIZ / ".streamlit" / "secrets.toml"
    if not caminho.exists():
        sys.exit("Crie .streamlit/secrets.toml a partir de secrets.toml.example antes de rodar.")
    return tomllib.loads(caminho.read_text(encoding="utf-8"))


def letra(n):  # 1 -> A
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--so-aviso", action="store_true",
                    help="a aba Histórico só mostra aviso, em vez de bloquear a edição")
    args = ap.parse_args()

    import gspread

    seg = carregar_segredos()
    cliente = gspread.service_account_from_dict(dict(seg["gcp_service_account"]))
    url = seg["planilha"]["url"]
    ss = cliente.open_by_url(url) if url.startswith("http") else cliente.open_by_key(url)
    email_sa = seg["gcp_service_account"]["client_email"]
    fuso = seg.get("app", {}).get("fuso", "America/Bahia")
    print(f"Planilha: {ss.title}")

    existentes = {w.title: w for w in ss.worksheets()}
    abas = {}
    for i, (nome, colunas) in enumerate(COLUNAS.items()):
        if nome in existentes:
            ws = existentes[nome]
            if ws.col_count < len(colunas):
                ws.add_cols(len(colunas) - ws.col_count)
        else:
            ws = ss.add_worksheet(nome, rows=1000, cols=len(colunas), index=i)
            print(f"  aba criada: {nome}")
        ws.update(range_name="A1", values=[colunas])
        abas[nome] = ws

    # remove a "Página1"/"Sheet1" vazia de uma planilha nova
    for titulo, ws in existentes.items():
        if titulo not in COLUNAS and titulo in ("Página1", "Sheet1", "Planilha1") and len(ss.worksheets()) > 4:
            if not any(any(c for c in linha) for linha in ws.get_all_values()):
                ss.del_worksheet(ws)

    # listas padrão (só se a aba Listas estiver vazia)
    listas = abas[ABA_LISTAS]
    if len(listas.get_all_values()) <= 1:
        maior = max(len(v) for v in LISTAS_PADRAO.values())
        linhas = [[LISTAS_PADRAO[c][i] if i < len(LISTAS_PADRAO[c]) else "" for c in COLUNAS[ABA_LISTAS]]
                  for i in range(maior)]
        listas.update(range_name="A2", values=linhas)
        print("  aba Listas preenchida com as opções padrão")

    def col(aba, nome):
        return COLUNAS[aba].index(nome)  # base 0

    def faixa(aba, nome):
        c = col(aba, nome)
        return {"sheetId": abas[aba].id, "startRowIndex": 1, "startColumnIndex": c, "endColumnIndex": c + 1}

    def lista_de(origem):
        return {"condition": {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": origem}]},
                "showCustomUi": True, "strict": True}

    def validar(aba, nome, regra, aviso=""):
        regra = dict(regra)
        if aviso:
            regra["inputMessage"] = aviso
        return {"setDataValidation": {"range": faixa(aba, nome), "rule": regra}}

    def formato(aba, nome, padrao, tipo):
        return {"repeatCell": {"range": faixa(aba, nome),
                               "cell": {"userEnteredFormat": {"numberFormat": {"type": tipo, "pattern": padrao}}},
                               "fields": "userEnteredFormat.numberFormat"}}

    A, F, H, L = ABA_ASSINATURAS, ABA_FUNCIONARIOS, ABA_HISTORICO, ABA_LISTAS
    req = [
        {"updateSpreadsheetProperties": {"properties": {"locale": "pt_BR", "timeZone": fuso},
                                         "fields": "locale,timeZone"}},
        # listas suspensas puxadas da aba Listas
        validar(A, "Categoria", lista_de(f"='{L}'!$A$2:$A")),
        validar(F, "Departamento", lista_de(f"='{L}'!$B$2:$B")),
        validar(A, "Plano", lista_de(f"='{L}'!$C$2:$C")),
        validar(A, "Status", lista_de(f"='{L}'!$D$2:$D")),
        # múltipla escolha a partir do nome das assinaturas
        validar(F, "Assinaturas", {**lista_de(f"='{A}'!$B$2:$B"), "strict": False},
                "Escolha uma ou mais assinaturas"),
        validar(A, "Nome", {"condition": {"type": "TEXT_NOT_CONTAINS", "values": [{"userEnteredValue": ","}]},
                            "strict": True}, "Sem vírgula: a lista de múltipla escolha usa vírgula"),
        validar(A, "Valor (R$)", {"condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0"}]},
                                  "strict": True}, "Número maior que zero"),
        validar(A, "Vencimento", {"condition": {"type": "DATE_IS_VALID"}, "strict": True}, "Data dd/mm/aaaa"),
        validar(F, "E-mail", {"condition": {"type": "TEXT_IS_EMAIL"}, "strict": True}, "E-mail válido"),
        # formatos
        formato(A, "Valor (R$)", '"R$" #,##0.00', "CURRENCY"),
        formato(A, "Vencimento", "dd/mm/yyyy", "DATE"),
        formato(A, "Cadastrado em", "dd/mm/yyyy hh:mm", "DATE_TIME"),
        formato(F, "Cadastrado em", "dd/mm/yyyy hh:mm", "DATE_TIME"),
        formato(H, "Data e hora", "dd/mm/yyyy hh:mm:ss", "DATE_TIME"),
    ]
    for nome, ws in abas.items():
        n = len(COLUNAS[nome])
        req += [
            {"updateSheetProperties": {"properties": {"sheetId": ws.id, "gridProperties": {"frozenRowCount": 1}},
                                       "fields": "gridProperties.frozenRowCount"}},
            {"repeatCell": {
                "range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0,
                          "endColumnIndex": n},
                "cell": {"userEnteredFormat": {
                    "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                    "backgroundColor": {"red": 0.145, "green": 0.388, "blue": 0.922}}},
                "fields": "userEnteredFormat(textFormat,backgroundColor)"}},
            {"autoResizeDimensions": {"dimensions": {"sheetId": ws.id, "dimension": "COLUMNS",
                                                     "startIndex": 0, "endIndex": n}}},
        ]

    # proteções: coluna ID e aba Histórico (o app e o dono continuam podendo gravar)
    ja = {(p.get("range", {}).get("sheetId"), p.get("description")) for p in _protecoes(ss)}
    def proteger(descricao, faixa_, so_aviso=False):
        if (faixa_["sheetId"], descricao) in ja:
            return None
        p = {"range": faixa_, "description": descricao}
        if args.so_aviso or so_aviso:
            p["warningOnly"] = True
        else:
            p["editors"] = {"users": [email_sa]}
        return {"addProtectedRange": {"protectedRange": p}}

    for aba in (A, F):
        # Só aviso: um bloqueio total impediria a equipe de ordenar a aba.
        r = proteger("ID gerado pelo app", faixa(aba, "ID"), so_aviso=True)
        if r:
            req.append(r)
    r = proteger("Histórico automático", {"sheetId": abas[H].id})
    if r:
        req.append(r)

    ss.batch_update({"requests": req})
    print("Validações, formatos e proteções aplicados.")
    print("\nFalta 1 passo manual: na aba Funcionários, coluna Assinaturas > Dados > Validação de dados >"
          " marque 'Permitir seleções múltiplas'.")
    print("Depois instale o Apps Script (apps_script/historico.gs) e rode a função instalarGatilho.")


def _protecoes(ss):
    try:
        meta = ss.fetch_sheet_metadata({"fields": "sheets(protectedRanges)"})
        return [p for s in meta.get("sheets", []) for p in s.get("protectedRanges", [])]
    except Exception:
        return []


if __name__ == "__main__":
    main()
