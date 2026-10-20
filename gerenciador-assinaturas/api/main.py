"""Aplicacao FastAPI do Licenzy e entrega da SPA React."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import auth
from api.rotas import assinaturas, dashboard, historico, pendencias, pessoas, projetos, relatorios, sistema
from servicos.cadastros import ConflitoEdicao, ErroValidacao
from servicos.planilha import ErroPlanilha

app = FastAPI(title="Licenzy API", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ErroValidacao)
async def erro_validacao(_: Request, exc: ErroValidacao):
    return JSONResponse(status_code=422, content={"detail": {"erros": exc.erros}})


@app.exception_handler(ConflitoEdicao)
async def conflito(_: Request, exc: ConflitoEdicao):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ErroPlanilha)
async def erro_planilha(_: Request, exc: ErroPlanilha):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(RequestValidationError)
async def entrada_invalida(_: Request, exc: RequestValidationError):
    erros = {".".join(map(str, item["loc"][1:])): item["msg"] for item in exc.errors()}
    return JSONResponse(status_code=422, content={"detail": {"erros": erros}})


app.include_router(auth.router)
app.include_router(sistema.router)
app.include_router(dashboard.router)
app.include_router(assinaturas.router)
app.include_router(pessoas.router)
app.include_router(projetos.router)
app.include_router(historico.router)
app.include_router(pendencias.router)
app.include_router(relatorios.router)


@app.get("/api/health", include_in_schema=False)
def health():
    return {"status": "ok"}


WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"
if WEB_DIST.exists():
    app.frontend("/", directory=str(WEB_DIST), fallback="index.html")
