"""Cria ou atualiza (por e-mail) as contas de acesso do Licenzy.

As senhas vêm só de variáveis de ambiente; a planilha recebe apenas o hash.

  # PowerShell
  $env:LICENZY_SENHA_FINANCEIRO="<senha do financeiro>"
  $env:LICENZY_SENHA_SUPORTE="<senha do suporte>"
  python scripts/criar_usuarios.py

Para trocar a senha de uma conta só, defina a variável do perfil dela e rode:
  python scripts/criar_usuarios.py --email financeiro@reconcavo.org.br
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from servicos import planilha  # noqa: E402
from servicos.esquema import ABA_USUARIOS, PERFIL_FINANCEIRO, PERFIL_SUPORTE  # noqa: E402
from servicos.usuarios import salvar_usuario  # noqa: E402

CONTAS = (
    ("Financeiro", "financeiro@reconcavo.org.br", PERFIL_FINANCEIRO, "LICENZY_SENHA_FINANCEIRO"),
    ("Suporte", "suporte@reconcavo.org.br", PERFIL_SUPORTE, "LICENZY_SENHA_SUPORTE"),
)
VARIAVEL_POR_PERFIL = {perfil: variavel for _, _, perfil, variavel in CONTAS}


def _conta_por_email(email: str) -> tuple[str, str, str, str]:
    """Conta já cadastrada (e-mail pode ter sido trocado na planilha) ou uma das iniciais."""
    alvo = email.strip().casefold()
    usuarios = planilha.ler_fresco(ABA_USUARIOS)
    if not usuarios.empty:
        achados = usuarios[usuarios["E-mail"].astype(str).str.strip().str.casefold() == alvo]
        if not achados.empty:
            registro = achados.iloc[0]
            perfil = str(registro["Perfil"]).strip().casefold()
            return str(registro["Nome"]), str(registro["E-mail"]), perfil, VARIAVEL_POR_PERFIL.get(perfil, "")
    for conta in CONTAS:
        if conta[1] == alvo:
            return conta
    raise SystemExit(f"Nenhuma conta com o e-mail {email}. Confira a aba Usuários.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", help="Atualiza só a conta com este e-mail.")
    args = parser.parse_args()
    contas = [_conta_por_email(args.email)] if args.email else list(CONTAS)

    faltando = [variavel for *_, variavel in contas if not os.environ.get(variavel)]
    if faltando:
        raise SystemExit("Defina a(s) variável(is) de ambiente: " + ", ".join(faltando))
    for nome, email, perfil, variavel in contas:
        try:
            id_ = salvar_usuario(nome, email, perfil, os.environ[variavel])
        except ValueError as exc:
            raise SystemExit(f"{email}: {exc}") from exc
        print(f"Conta salva: {id_} · {email.lower()} · {perfil}")


if __name__ == "__main__":
    main()
