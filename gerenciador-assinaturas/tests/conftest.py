import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ["GA_FORCAR_LOCAL"] = "1"  # testes nunca tocam no Google Sheets


@pytest.fixture
def planilha_vazia(tmp_path, monkeypatch):
    """Planilha local nova e vazia para cada teste."""
    from servicos import planilha

    monkeypatch.setattr(planilha, "CAMINHO_LOCAL", tmp_path / "planilha_teste.xlsx")
    planilha.limpar_cache()
    yield planilha
    planilha.limpar_cache()
