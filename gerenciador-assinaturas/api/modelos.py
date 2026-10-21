"""Modelos de entrada da API; as validacoes oficiais continuam em servicos.cadastros."""
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LoginIn(BaseModel):
    email: str
    senha: str


class AssinaturaDados(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nome: str = Field(alias="Nome")
    logo: str = Field(default="", alias="Logo (URL)")
    categoria: str | None = Field(default=None, alias="Categoria")
    plano: str | None = Field(default=None, alias="Plano")
    valor: float | None = Field(default=None, alias="Valor (R$)")
    vencimento: date | None = Field(default=None, alias="Vencimento")
    status: str | None = Field(default=None, alias="Status")


class AssinaturaIn(BaseModel):
    dados: AssinaturaDados
    original: dict[str, Any] | None = None


class PessoaDados(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nome: str = Field(alias="Nome completo")
    email: str = Field(alias="E-mail")
    departamento: str | None = Field(default=None, alias="Departamento")
    cargo: str = Field(default="", alias="Cargo")


class PessoaIn(BaseModel):
    dados: PessoaDados
    original: dict[str, Any] | None = None


class ProjetoDados(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nome: str = Field(alias="Nome")
    cliente: str = Field(default="", alias="Cliente")
    responsavel: str = Field(default="", alias="Responsavel", validation_alias="Responsavel")
    departamento: str = Field(default="", alias="Departamento")
    observacoes: str = Field(default="", alias="Observacoes")


class MembroIn(BaseModel):
    pessoa_id: str
    assinaturas_ids: list[str] = Field(min_length=1)


class ProjetoIn(BaseModel):
    dados: ProjetoDados
    equipe: list[MembroIn] = Field(min_length=1)
    original: dict[str, Any] | None = None


class OriginalIn(BaseModel):
    original: dict[str, Any] | None = None


class RecusaIn(OriginalIn):
    motivo: str = Field(min_length=10)
