"""Login individual, sessão assinada, perfis e bloqueio de tentativas."""
from __future__ import annotations

import os
import threading
import time
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from api.modelos import LoginIn
from servicos import planilha, usuarios
from servicos.esquema import PERFIL_FINANCEIRO
from servicos.usuarios import Usuario

MAX_TENTATIVAS = 5
BLOQUEIO_SEGUNDOS = 5 * 60
SESSAO_MAX_SEGUNDOS = 12 * 60 * 60
COOKIE = "licenzy_session"
_HASH_FALSO = usuarios.gerar_hash("credencial-inexistente")

router = APIRouter(prefix="/api", tags=["autenticacao"])
_trava = threading.Lock()
_tentativas: dict[str, dict[str, float | int]] = {}


def _redis():
    url = os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        return None
    from upstash_redis import Redis
    return Redis(url=url, token=token)


def _ip(request: Request) -> str:
    encaminhado = request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return encaminhado or (request.client.host if request.client else "desconhecido")


def _serializer() -> URLSafeTimedSerializer:
    chave = os.environ.get("LICENZY_SESSION_KEY")
    if not chave:
        if not planilha.modo_local():
            raise HTTPException(503, "Defina LICENZY_SESSION_KEY nas variáveis do ambiente.")
        chave = "licenzy-local-development-only"
    return URLSafeTimedSerializer(chave, salt="licenzy-session-v2")


def _situacao(chave: str) -> tuple[int, int]:
    redis = _redis()
    if redis:
        erros = int(redis.get(chave) or 0)
        return erros, max(int(redis.ttl(chave) or 0), 0)
    with _trava:
        info = _tentativas.get(chave, {"erros": 0, "ate": 0.0})
        if float(info["ate"]) and time.time() >= float(info["ate"]):
            info = {"erros": 0, "ate": 0.0}
            _tentativas[chave] = info
        return int(info["erros"]), max(0, int(float(info["ate"]) - time.time()))


def _registrar_erro(chave: str) -> tuple[int, int]:
    redis = _redis()
    if redis:
        erros = int(redis.incr(chave))
        if erros in (1, MAX_TENTATIVAS):
            redis.expire(chave, BLOQUEIO_SEGUNDOS)
        return erros, int(redis.ttl(chave) or BLOQUEIO_SEGUNDOS)
    with _trava:
        info = _tentativas.setdefault(chave, {"erros": 0, "ate": 0.0})
        info["erros"] = int(info["erros"]) + 1
        if int(info["erros"]) >= MAX_TENTATIVAS:
            info["ate"] = time.time() + BLOQUEIO_SEGUNDOS
        return int(info["erros"]), max(0, int(float(info["ate"]) - time.time()))


def _zerar(*chaves: str) -> None:
    redis = _redis()
    if redis:
        if chaves:
            redis.delete(*chaves)
        return
    with _trava:
        for chave in chaves:
            _tentativas.pop(chave, None)


def _dados_token(token: str, *, verificar_tempo: bool = True) -> dict | None:
    try:
        return _serializer().loads(token, max_age=SESSAO_MAX_SEGUNDOS if verificar_tempo else None)
    except (BadSignature, SignatureExpired):
        return None


def usuario_do_cookie(token: str | None) -> Usuario | None:
    if not token:
        return None
    dados = _dados_token(token)
    if not dados or not dados.get("autenticado"):
        return None
    return Usuario(
        id=str(dados.get("uid", "")), nome=str(dados.get("nome", "")),
        email=str(dados.get("email", "")), perfil=str(dados.get("perfil", "")),
    )


def exigir_sessao(licenzy_session: Annotated[str | None, Cookie()] = None) -> Usuario:
    usuario_token = usuario_do_cookie(licenzy_session)
    if usuario_token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada.")
    atual = usuarios.buscar_por_id(usuario_token.id)
    if atual is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário inativo ou inexistente.")
    return atual


def exigir_perfil(*perfis: str):
    def _dependencia(usuario: Usuario = Depends(exigir_sessao)) -> Usuario:
        if usuario.perfil not in perfis:
            raise HTTPException(403, "Seu perfil não permite esta ação.")
        return usuario
    return _dependencia


Sessao = Annotated[Usuario, Depends(exigir_sessao)]
Financeiro = Annotated[Usuario, Depends(exigir_perfil(PERFIL_FINANCEIRO))]


@router.post("/login")
def login(corpo: LoginIn, request: Request, response: Response):
    email = corpo.email.strip().lower()
    chaves = (f"login:{_ip(request)}", f"login:email:{email}")
    situacoes = [_situacao(chave) for chave in chaves]
    if any(erros >= MAX_TENTATIVAS for erros, _ in situacoes):
        segundos = max(segundos for _, segundos in situacoes)
        raise HTTPException(429, detail={"mensagem": "Muitas tentativas erradas.", "tente_em_segundos": segundos})

    registro = usuarios.buscar_por_email(email)
    hash_guardado = str(registro.get("Senha (hash)", "")) if registro else _HASH_FALSO
    if not usuarios.conferir(corpo.senha, hash_guardado):
        resultados = [_registrar_erro(chave) for chave in chaves]
        erros = max(resultado[0] for resultado in resultados)
        segundos = max(resultado[1] for resultado in resultados)
        restantes = max(0, MAX_TENTATIVAS - erros)
        raise HTTPException(429 if restantes == 0 else 401, detail={
            "mensagem": "E-mail ou senha incorretos.",
            "tentativas_restantes": restantes, "tente_em_segundos": segundos,
        })

    usuario = usuarios.usuario_de_registro(registro)
    _zerar(*chaves)
    usuarios.registrar_acesso(usuario.id)
    token = _serializer().dumps({
        "autenticado": True, "uid": usuario.id, "perfil": usuario.perfil,
        "nome": usuario.nome, "email": usuario.email,
    })
    response.set_cookie(
        COOKIE, token, httponly=True,
        secure=bool(os.environ.get("VERCEL") or request.url.scheme == "https"),
        samesite="strict", path="/",
    )
    return {"autenticado": True, "usuario": {"nome": usuario.nome, "email": usuario.email, "perfil": usuario.perfil}}


@router.get("/sessao")
def sessao(usuario: Sessao):
    return {
        "autenticado": True, "modo_local": planilha.modo_local(),
        "usuario": {"nome": usuario.nome, "email": usuario.email, "perfil": usuario.perfil},
    }


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE, path="/")
    return {"autenticado": False}
