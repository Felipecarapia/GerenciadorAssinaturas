"""Usuários de acesso, hash de senha e contexto da requisição atual."""
from __future__ import annotations

import base64
import contextvars
import hashlib
import hmac
import os
from dataclasses import dataclass

from servicos import planilha
from servicos.calculos import normalizar
from servicos.esquema import ABA_USUARIOS, PERFIL_FINANCEIRO, PERFIL_SUPORTE


@dataclass(frozen=True)
class Usuario:
    id: str
    nome: str
    email: str
    perfil: str


usuario_atual: contextvars.ContextVar[Usuario | None] = contextvars.ContextVar(
    "usuario_atual", default=None,
)

_N, _R, _P = 2**14, 8, 1
PERFIS = {PERFIL_FINANCEIRO, PERFIL_SUPORTE}


def gerar_hash(senha: str) -> str:
    sal = os.urandom(16)
    resumo = hashlib.scrypt(senha.encode(), salt=sal, n=_N, r=_R, p=_P, dklen=32)
    return "$".join((
        "scrypt", str(_N), str(_R), str(_P),
        base64.b64encode(sal).decode(), base64.b64encode(resumo).decode(),
    ))


def conferir(senha: str, guardado: str) -> bool:
    try:
        algoritmo, n, r, p, sal, esperado = guardado.split("$")
        if algoritmo != "scrypt":
            return False
        calculado = hashlib.scrypt(
            senha.encode(), salt=base64.b64decode(sal),
            n=int(n), r=int(r), p=int(p), dklen=32,
        )
        return hmac.compare_digest(calculado, base64.b64decode(esperado))
    except (ValueError, TypeError, base64.binascii.Error):
        return False


def _ativo(valor: object) -> bool:
    return normalizar(valor) in {"sim", "true", "1", "ativo", "ativa"}


def _para_usuario(registro: dict) -> Usuario:
    return Usuario(
        id=str(registro["ID"]), nome=str(registro.get("Nome", "")),
        email=str(registro.get("E-mail", "")).strip().lower(),
        perfil=normalizar(registro.get("Perfil")),
    )


def garantir_usuarios_locais() -> None:
    if not planilha.modo_local() or not planilha.ler_fresco(ABA_USUARIOS).empty:
        return
    for nome, email, perfil in (
        ("Financeiro", "financeiro@reconcavo.org.br", PERFIL_FINANCEIRO),
        ("Suporte", "suporte@reconcavo.org.br", PERFIL_SUPORTE),
    ):
        salvar_usuario(nome, email, perfil, "demo", permitir_senha_demo=True)


def buscar_por_email(email: str) -> dict | None:
    garantir_usuarios_locais()
    usuarios = planilha.ler(ABA_USUARIOS)
    if usuarios.empty:
        return None
    encontrados = usuarios[
        usuarios["E-mail"].astype(str).str.strip().str.casefold() == str(email).strip().casefold()
    ]
    if encontrados.empty or not _ativo(encontrados.iloc[0].get("Ativo")):
        return None
    return encontrados.iloc[0].to_dict()


def buscar_por_id(id_: str) -> Usuario | None:
    garantir_usuarios_locais()
    registro = planilha.ler_registro(ABA_USUARIOS, id_)
    if registro is None or not _ativo(registro.get("Ativo")):
        return None
    usuario = _para_usuario(registro)
    return usuario if usuario.perfil in PERFIS else None


def registrar_acesso(id_: str) -> None:
    from servicos.cadastros import agora

    planilha.atualizar_campos(
        ABA_USUARIOS, id_, {"Último acesso": agora().strftime("%Y-%m-%d %H:%M:%S")},
    )
    planilha.limpar_cache()


def salvar_usuario(
    nome: str, email: str, perfil: str, senha: str,
    *, permitir_senha_demo: bool = False,
) -> str:
    from servicos.cadastros import agora

    perfil_normalizado = normalizar(perfil)
    if perfil_normalizado not in PERFIS:
        raise ValueError("Perfil deve ser financeiro ou suporte.")
    if len(senha) < 10 and not (permitir_senha_demo and senha == "demo"):
        raise ValueError("A senha precisa ter pelo menos 10 caracteres.")
    email_normalizado = str(email).strip().lower()
    existentes = planilha.ler_fresco(ABA_USUARIOS)
    encontrado = existentes[
        existentes["E-mail"].astype(str).str.strip().str.casefold() == email_normalizado.casefold()
    ] if not existentes.empty else existentes
    momento = agora().strftime("%Y-%m-%d %H:%M:%S")
    registro = {
        "Nome": " ".join(str(nome).split()), "E-mail": email_normalizado,
        "Perfil": perfil_normalizado, "Senha (hash)": gerar_hash(senha),
        "Ativo": "Sim", "Último acesso": "", "Cadastrado em": momento,
    }
    if encontrado.empty:
        id_ = planilha.novo_id(ABA_USUARIOS)
        planilha.inserir(ABA_USUARIOS, [{"ID": id_, **registro}])
    else:
        atual = encontrado.iloc[0].to_dict()
        id_ = str(atual["ID"])
        registro["Cadastrado em"] = atual.get("Cadastrado em") or momento
        registro["Último acesso"] = atual.get("Último acesso") or ""
        planilha.atualizar(ABA_USUARIOS, id_, {"ID": id_, **registro})
    planilha.limpar_cache()
    return id_


def usuario_de_registro(registro: dict) -> Usuario:
    return _para_usuario(registro)
