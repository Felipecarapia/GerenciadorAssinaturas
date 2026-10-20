"""Login por senha, sessao assinada e bloqueio de tentativas por IP."""
from __future__ import annotations

import hmac
import os
import threading
import time
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from api.modelos import LoginIn
from servicos import planilha

MAX_TENTATIVAS = 5
BLOQUEIO_SEGUNDOS = 5 * 60
SESSAO_MAX_SEGUNDOS = 12 * 60 * 60
COOKIE = "licenzy_session"
SENHA_DEMO = "demo"

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


def _senha_configurada() -> str | None:
    senha_ambiente = os.environ.get("LICENZY_APP_PASSWORD")
    if senha_ambiente is not None:
        return senha_ambiente or None
    senha = planilha._segredo("app", "senha")  # noqa: SLF001 - mesma fonte usada pelo legado
    return str(senha) if senha else None


def _serializer() -> URLSafeTimedSerializer:
    chave = os.environ.get("LICENZY_SESSION_KEY")
    if not chave:
        if not planilha.modo_local():
            raise HTTPException(503, "Defina LICENZY_SESSION_KEY nas variaveis do ambiente.")
        chave = "licenzy-local-development-only"
    return URLSafeTimedSerializer(chave, salt="licenzy-session-v1")


def _situacao(ip: str) -> tuple[int, int]:
    redis = _redis()
    if redis:
        chave = f"login:{ip}"
        erros = int(redis.get(chave) or 0)
        ttl = int(redis.ttl(chave) or 0)
        return erros, max(ttl, 0)
    with _trava:
        info = _tentativas.get(ip, {"erros": 0, "ate": 0.0})
        if float(info["ate"]) and time.time() >= float(info["ate"]):
            info = {"erros": 0, "ate": 0.0}
            _tentativas[ip] = info
        return int(info["erros"]), max(0, int(float(info["ate"]) - time.time()))


def _registrar_erro(ip: str) -> tuple[int, int]:
    redis = _redis()
    if redis:
        chave = f"login:{ip}"
        erros = int(redis.incr(chave))
        if erros in (1, MAX_TENTATIVAS):
            redis.expire(chave, BLOQUEIO_SEGUNDOS)
        return erros, int(redis.ttl(chave) or BLOQUEIO_SEGUNDOS)
    with _trava:
        info = _tentativas.setdefault(ip, {"erros": 0, "ate": 0.0})
        info["erros"] = int(info["erros"]) + 1
        if int(info["erros"]) >= MAX_TENTATIVAS:
            info["ate"] = time.time() + BLOQUEIO_SEGUNDOS
        return int(info["erros"]), max(0, int(float(info["ate"]) - time.time()))


def _zerar(ip: str) -> None:
    redis = _redis()
    if redis:
        redis.delete(f"login:{ip}")
        return
    with _trava:
        _tentativas.pop(ip, None)


def exigir_sessao(licenzy_session: Annotated[str | None, Cookie()] = None) -> None:
    if not licenzy_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessao nao autenticada.")
    try:
        dados = _serializer().loads(licenzy_session, max_age=SESSAO_MAX_SEGUNDOS)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessao expirada.") from None
    if not dados.get("autenticado"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessao invalida.")


Sessao = Annotated[None, Depends(exigir_sessao)]


@router.post("/login")
def login(corpo: LoginIn, request: Request, response: Response):
    ip = _ip(request)
    erros, segundos = _situacao(ip)
    if erros >= MAX_TENTATIVAS:
        raise HTTPException(429, detail={"mensagem": "Muitas tentativas erradas.", "tente_em_segundos": segundos})

    configurada = _senha_configurada()
    demo = configurada is None and planilha.modo_local()
    if configurada is None and not demo:
        raise HTTPException(503, "A senha de acesso nao esta configurada.")
    esperada = configurada or SENHA_DEMO
    if not hmac.compare_digest(corpo.senha.encode("utf-8"), esperada.encode("utf-8")):
        erros, segundos = _registrar_erro(ip)
        restantes = max(0, MAX_TENTATIVAS - erros)
        codigo = 429 if restantes == 0 else 401
        raise HTTPException(codigo, detail={"mensagem": "Senha incorreta.", "tentativas_restantes": restantes, "tente_em_segundos": segundos})

    _zerar(ip)
    token = _serializer().dumps({"autenticado": True})
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=bool(os.environ.get("VERCEL") or request.url.scheme == "https"),
        samesite="strict",
        path="/",
    )
    return {"autenticado": True, "modo_demo": demo}


@router.get("/sessao")
def sessao(_: Sessao):
    return {"autenticado": True, "modo_local": planilha.modo_local()}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE, path="/")
    return {"autenticado": False}
