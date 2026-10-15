"""Preenche a planilha com 20 assinaturas e 15 pessoas fictícias.

Use SÓ na planilha de testes (o link em .streamlit/secrets.toml) ou no modo local.

    python scripts/dados_exemplo.py              # recusa se já houver dados
    python scripts/dados_exemplo.py --pendencias # inclui 2 linhas com problemas, para testar o painel
    python scripts/dados_exemplo.py --local      # na planilha local de demonstração
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.chdir(RAIZ)  # st.secrets lê .streamlit/secrets.toml da pasta atual


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pendencias", action="store_true", help="inclui linhas com problemas de propósito")
    ap.add_argument("--local", action="store_true", help="usa a planilha local de demonstração")
    ap.add_argument("--forcar", action="store_true", help="acrescenta mesmo se já houver dados")
    args = ap.parse_args()
    if args.local:
        os.environ["GA_FORCAR_LOCAL"] = "1"

    from servicos import exemplo, planilha
    from servicos.cadastros import agora
    from servicos.esquema import ABA_ASSINATURAS, ABA_FUNCIONARIOS

    print(f"Base de dados: {planilha.motor().nome}")
    ja_tem = len(planilha.ler_fresco(ABA_ASSINATURAS)) + len(planilha.ler_fresco(ABA_FUNCIONARIOS))
    if ja_tem and not args.forcar:
        sys.exit(f"A planilha já tem {ja_tem} linha(s) de dados. Use --forcar para acrescentar mesmo assim.")
    resposta = input("Isto grava dados FICTÍCIOS na planilha acima. Digite SIM para continuar: ")
    if resposta.strip().upper() != "SIM":
        sys.exit("Cancelado.")
    exemplo.carregar(agora(), com_pendencias=args.pendencias)
    print("Pronto: 20 assinaturas e 15 pessoas de exemplo gravadas.")


if __name__ == "__main__":
    main()
