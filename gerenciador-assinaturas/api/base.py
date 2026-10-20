"""Leitura compartilhada e serializacao segura para a API."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import pandas as pd

from servicos import calculos as calc
from servicos import planilha
from servicos.cadastros import agora
from servicos.esquema import (
    ABA_ASSINATURAS,
    ABA_FUNCIONARIOS,
    ABA_HISTORICO,
    ABA_PROJETOS,
    ABA_USOS_PROJETO,
)


@dataclass
class Base:
    assinaturas: pd.DataFrame
    funcionarios: pd.DataFrame
    historico: pd.DataFrame
    listas: dict[str, list[str]]
    projetos: pd.DataFrame
    usos_projeto: pd.DataFrame

    @property
    def nomes_assinaturas(self) -> list[str]:
        if self.assinaturas.empty:
            return []
        return sorted(str(nome) for nome in self.assinaturas["Nome"] if str(nome).strip())


def base() -> Base:
    assinaturas = planilha.ler(ABA_ASSINATURAS)
    return Base(
        assinaturas=calc.preparar_assinaturas(assinaturas, agora().date()),
        funcionarios=planilha.ler(ABA_FUNCIONARIOS),
        historico=planilha.ler(ABA_HISTORICO),
        listas=planilha.listas(),
        projetos=planilha.ler(ABA_PROJETOS),
        usos_projeto=planilha.ler(ABA_USOS_PROJETO),
    )


def valor_json(valor: Any) -> Any:
    if isinstance(valor, dict):
        return {str(chave): valor_json(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple, set)):
        return [valor_json(item) for item in valor]
    if isinstance(valor, (date, datetime, pd.Timestamp)):
        return valor.isoformat()
    if hasattr(valor, "item"):
        try:
            valor = valor.item()
        except (TypeError, ValueError):
            pass
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    return valor


def df_json(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    return [valor_json(registro) for registro in df.to_dict(orient="records")]
