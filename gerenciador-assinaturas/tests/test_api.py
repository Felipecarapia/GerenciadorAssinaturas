import os

import pytest
from fastapi.testclient import TestClient

from api import auth
from api.main import app


@pytest.fixture
def cliente(planilha_vazia, monkeypatch):
    monkeypatch.setenv("LICENZY_SESSION_KEY", "chave-segura-exclusiva-dos-testes")
    monkeypatch.setattr(auth, "_senha_configurada", lambda: None)
    monkeypatch.setattr(auth, "_redis", lambda: None)
    auth._tentativas.clear()
    with TestClient(app) as client:
        yield client
    auth._tentativas.clear()


@pytest.fixture
def autenticado(cliente):
    resposta = cliente.post("/api/login", json={"senha": "demo"})
    assert resposta.status_code == 200
    return cliente


def test_rotas_exigem_login(cliente):
    assert cliente.get("/api/dashboard").status_code == 401
    assert cliente.get("/api/health").status_code == 200


def test_login_sessao_e_logout(cliente):
    assert cliente.post("/api/login", json={"senha": "errada"}).status_code == 401
    assert cliente.post("/api/login", json={"senha": "demo"}).status_code == 200
    assert cliente.get("/api/sessao").json()["autenticado"] is True
    assert cliente.post("/api/logout").status_code == 200
    assert cliente.get("/api/sessao").status_code == 401


def test_bloqueia_apos_cinco_erros(cliente):
    respostas = [cliente.post("/api/login", json={"senha": "errada"}) for _ in range(5)]
    assert [r.status_code for r in respostas] == [401, 401, 401, 401, 429]
    bloqueada = cliente.post("/api/login", json={"senha": "demo"})
    assert bloqueada.status_code == 429


def test_dashboard_vazio_e_listas(autenticado):
    resposta = autenticado.get("/api/dashboard")
    assert resposta.status_code == 200
    assert resposta.json()["indicadores"]["total_ativas"] == 0
    assert "Categorias" in autenticado.get("/api/listas").json()


def test_validacao_crud_e_download(autenticado):
    pessoa = autenticado.post("/api/pessoas", json={
        "dados": {"Nome completo": "Ana Teste", "E-mail": "ana@teste.com", "Departamento": "TI", "Cargo": "Analista"},
        "assinaturas": [],
    })
    assert pessoa.status_code == 201
    pessoa_id = pessoa.json()["id"]

    invalida = autenticado.post("/api/assinaturas", json={
        "dados": {"Nome": "", "Logo (URL)": "", "Categoria": "", "Plano": "Mensal", "Valor (R$)": 0, "Vencimento": None, "Status": "Ativa"},
        "usuarios_ids": [],
    })
    assert invalida.status_code == 422
    assert "Nome" in invalida.json()["detail"]["erros"]

    criada = autenticado.post("/api/assinaturas", json={
        "dados": {"Nome": "Ferramenta Teste", "Logo (URL)": "", "Categoria": "Desenvolvimento", "Plano": "Mensal", "Valor (R$)": 120, "Vencimento": "2027-01-20", "Status": "Ativa"},
        "usuarios_ids": [pessoa_id],
    })
    assert criada.status_code == 201
    assinatura_id = criada.json()["id"]
    lista = autenticado.get("/api/assinaturas").json()
    assert lista["itens"][0]["usuarios_ids"] == [pessoa_id]

    excel = autenticado.get("/api/assinaturas/exportar/xlsx")
    assert excel.status_code == 200
    assert excel.content.startswith(b"PK")

    detalhe = autenticado.get(f"/api/assinaturas/{assinatura_id}")
    assert detalhe.status_code == 200
    assert detalhe.json()["item"]["Nome"] == "Ferramenta Teste"

    projeto = autenticado.post("/api/projetos", json={
        "dados": {"Nome": "Projeto API", "Cliente": "Cliente", "Responsavel": "Ana", "Departamento": "TI", "Status": "Ativo", "Observacoes": "Teste"},
        "assinaturas_ids": [assinatura_id],
    })
    assert projeto.status_code == 201
    projetos = autenticado.get("/api/projetos").json()["itens"]
    assert projetos[0]["assinaturas_ids"] == [assinatura_id]

    relatorio = autenticado.get("/api/relatorios/categorias.xlsx")
    assert relatorio.status_code == 200
    assert relatorio.content.startswith(b"PK")


def test_conflito_vira_409(autenticado, monkeypatch):
    from api.rotas import assinaturas
    from servicos.cadastros import ConflitoEdicao

    def conflitar(*args, **kwargs):
        raise ConflitoEdicao("Alguem alterou este registro.")

    monkeypatch.setattr(assinaturas.cadastros, "salvar_assinatura", conflitar)
    resposta = autenticado.post("/api/assinaturas", json={
        "dados": {"Nome": "Teste", "Logo (URL)": "", "Categoria": "Design", "Plano": "Vitalicio", "Valor (R$)": 1, "Vencimento": None, "Status": "Ativa"},
        "usuarios_ids": ["F-1"],
    })
    assert resposta.status_code == 409


def test_spa_e_entregue_pelo_fastapi(cliente):
    resposta = cliente.get("/login", headers={"accept": "text/html"})
    assert resposta.status_code == 200
    assert "Licenzy" in resposta.text
