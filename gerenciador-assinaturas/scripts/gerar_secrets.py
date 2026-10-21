"""Gera o .streamlit/secrets.toml a partir do .json da conta de serviço.

Evita copiar campo por campo (a private_key quebra fácil). Uso:

    python scripts/gerar_secrets.py

O script pergunta o caminho do .json e o link da planilha. As contas de acesso
são criadas separadamente por ``scripts/criar_usuarios.py``.
"""
from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / ".streamlit" / "secrets.toml"


def texto_toml(v) -> str:
    # As aspas e escapes de JSON (\n, \", \\) também são válidos em TOML.
    return json.dumps(str(v), ensure_ascii=False)


def main():
    if DESTINO.exists():
        r = input(f"{DESTINO} já existe. Substituir? (s/N) ").strip().lower()
        if r != "s":
            sys.exit("Nada foi alterado.")

    caminho = input("Caminho do arquivo .json da conta de serviço: ").strip().strip('"').strip("'")
    try:
        chave = json.loads(Path(caminho).expanduser().read_text(encoding="utf-8"))
    except Exception as erro:  # noqa: BLE001
        sys.exit(f"Não consegui ler o .json: {erro}")
    if chave.get("type") != "service_account":
        sys.exit('Esse .json não é de uma conta de serviço (falta "type": "service_account").')

    url = input("Link da planilha do Google: ").strip()
    if "docs.google.com/spreadsheets" not in url and len(url) < 20:
        sys.exit("Link da planilha inválido.")

    linhas = [
        "# Gerado por scripts/gerar_secrets.py. NUNCA envie este arquivo para o GitHub.",
        "",
        "[app]",
        'fuso = "America/Bahia"',
        "",
        "[planilha]",
        f"url = {texto_toml(url)}",
        "",
        "[gcp_service_account]",
    ]
    linhas += [f"{k} = {texto_toml(v)}" for k, v in chave.items()]
    conteudo = "\n".join(linhas) + "\n"
    tomllib.loads(conteudo)  # confere se o TOML ficou válido antes de gravar

    DESTINO.parent.mkdir(exist_ok=True)
    DESTINO.write_text(conteudo, encoding="utf-8")
    print(f"\nPronto: {DESTINO}")
    print(f"Conta de serviço: {chave.get('client_email')}")
    print("Confira se a planilha está compartilhada como Editor com esse e-mail.")


if __name__ == "__main__":
    main()
