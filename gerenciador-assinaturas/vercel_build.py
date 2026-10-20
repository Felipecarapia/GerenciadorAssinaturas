"""Build do frontend e materializacao dos segredos durante o deploy na Vercel."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def main() -> None:
    raiz = Path(__file__).resolve().parent
    subprocess.run(["npm", "ci"], cwd=raiz / "web", check=True, shell=os.name == "nt")
    subprocess.run(["npm", "run", "build"], cwd=raiz / "web", check=True, shell=os.name == "nt")

    conteudo = os.environ.get("LICENZY_SECRETS_TOML")
    if not conteudo:
        if os.environ.get("VERCEL"):
            raise SystemExit("Defina LICENZY_SECRETS_TOML nas variaveis de ambiente da Vercel.")
        print("LICENZY_SECRETS_TOML ausente; segredos locais foram preservados.")
        return
    destino = raiz / ".streamlit" / "secrets.toml"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(conteudo, encoding="utf-8")


if __name__ == "__main__":
    main()
