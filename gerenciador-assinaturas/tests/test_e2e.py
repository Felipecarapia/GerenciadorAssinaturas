"""Teste de ponta a ponta da interface React com Playwright.

Sobe o FastAPI em uma porta propria, usa uma planilha local temporaria preenchida
com dados ficticios e nunca le segredos ou dados reais.
"""
import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
WEB_DIST = RAIZ / "web" / "dist" / "index.html"
PRINTS = os.environ.get("GA_PRINTS")


def _porta_livre():
    with socket.socket() as servidor:
        servidor.bind(("127.0.0.1", 0))
        return servidor.getsockname()[1]


@pytest.fixture(scope="module")
def servidor(tmp_path_factory):
    if not WEB_DIST.exists():
        pytest.skip("Execute `cd web && npm ci && npm run build` antes do E2E.")
    caminho = tmp_path_factory.mktemp("e2e-react") / "planilha_e2e.xlsx"
    env = {
        **os.environ,
        "GA_PLANILHA_LOCAL": str(caminho),
        "GA_FORCAR_LOCAL": "1",
        "LICENZY_APP_PASSWORD": "demo",
        "LICENZY_SESSION_KEY": "chave-de-sessao-exclusiva-do-e2e",
        "PYTHONIOENCODING": "utf-8",
    }
    subprocess.run(
        [sys.executable, "-c", "from datetime import datetime; from servicos import exemplo; exemplo.carregar(datetime.now().replace(microsecond=0), com_pendencias=True)"],
        cwd=RAIZ,
        env=env,
        check=True,
        capture_output=True,
    )
    porta = _porta_livre()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", str(porta)],
        cwd=RAIZ,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{porta}"
    for _ in range(80):
        try:
            import urllib.request

            if urllib.request.urlopen(url + "/api/health", timeout=1).read():
                break
        except Exception:
            time.sleep(0.25)
    else:
        proc.terminate()
        raise RuntimeError("A API nao iniciou para o teste E2E.")
    yield url
    proc.terminate()
    proc.wait(10)


def _print(page, nome):
    if PRINTS:
        Path(PRINTS).mkdir(parents=True, exist_ok=True)
        page.wait_for_timeout(1_200)
        page.screenshot(path=str(Path(PRINTS) / f"{nome}.png"), full_page=True)


def _entrar(page, url):
    page.goto(url + "/login")
    page.get_by_label("Senha de acesso").fill("demo")
    page.get_by_role("button", name="Acessar plataforma").click()
    expect(page.get_by_role("heading", name="Dashboard")).to_be_visible(timeout=20_000)


def _sem_estouro_horizontal(page):
    largura = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert largura <= 2, f"A pagina excedeu a largura da tela em {largura}px"


def test_login_recusa_senha_errada(servidor, page):
    page.goto(servidor + "/login")
    page.get_by_label("Senha de acesso").fill("errada")
    page.get_by_role("button", name="Acessar plataforma").click()
    expect(page.get_by_text("Senha incorreta")).to_be_visible()
    _print(page, "00_login_react")


def test_percorre_telas(servidor, page):
    page.set_viewport_size({"width": 1440, "height": 1000})
    _entrar(page, servidor)
    expect(page.get_by_text("Gasto mensal").first).to_be_visible()
    expect(page.get_by_text("Alertas de vencimento")).to_be_visible()
    _print(page, "01_dashboard_react")

    for titulo, arquivo in [
        ("Assinaturas", "02_assinaturas_react"),
        ("Pessoas", "03_pessoas_react"),
        ("Projetos", "04_projetos_react"),
        ("Relatorios", "05_relatorios_react"),
        ("Historico", "06_historico_react"),
        ("Pendencias", "07_pendencias_react"),
    ]:
        rotulo = {"Relatorios": "Relatórios", "Historico": "Histórico", "Pendencias": "Pendências"}.get(titulo, titulo)
        page.get_by_role("link", name=rotulo).click()
        expect(page.get_by_role("heading", name=rotulo)).to_be_visible(timeout=20_000)
        _print(page, arquivo)


def test_cadastrar_assinatura_pelo_dialogo(servidor, page):
    page.set_viewport_size({"width": 1440, "height": 1000})
    _entrar(page, servidor)
    page.get_by_role("link", name="Assinaturas").click()
    page.get_by_role("button", name="Nova assinatura").first.click()
    janela = page.get_by_role("dialog")
    expect(janela).to_be_visible()
    janela.get_by_role("button", name="Salvar assinatura").click()
    expect(janela.get_by_text("Informe o nome.")).to_be_visible()

    nome = f"Teste E2E {datetime.now():%H%M%S}"
    janela.get_by_label("Nome *").fill(nome)
    janela.get_by_label("Categoria *").select_option(label="Design")
    janela.get_by_label("Plano *").select_option(label="Mensal")
    janela.get_by_label("Valor (R$) *").fill("99.90")
    janela.get_by_label("Vencimento").fill("2030-12-01")
    janela.get_by_text("Ana Beatriz Souza").click()
    janela.get_by_role("button", name="Salvar assinatura").click()
    expect(page.get_by_text("Assinatura salva.")).to_be_visible(timeout=20_000)
    page.get_by_label("Buscar por nome").fill(nome)
    expect(page.get_by_text(nome).first).to_be_visible()
    _print(page, "08_cadastro_react")


def test_celular(servidor, page):
    page.set_viewport_size({"width": 390, "height": 844})
    _entrar(page, servidor)
    expect(page.get_by_text("Gasto mensal").first).to_be_visible()
    _sem_estouro_horizontal(page)
    _print(page, "09_celular_react")


def test_estados_visuais_e_menu_de_acoes(servidor, page):
    page.set_viewport_size({"width": 1440, "height": 900})
    _entrar(page, servidor)

    card = page.get_by_test_id("featured-metric")
    destaque = page.get_by_test_id("featured-metric-accent")
    expect(destaque).to_have_css("opacity", "0")
    card.hover()
    expect(destaque).to_have_css("opacity", "1")

    page.get_by_role("link", name="Assinaturas").click()
    botoes = page.get_by_role("button", name=re.compile(r"^Ações de "))
    expect(botoes.first).to_be_visible(timeout=20_000)
    botoes.last.click()
    menu = page.get_by_role("menu", name=re.compile(r"^Ações de "))
    expect(menu).to_be_visible()
    assert menu.evaluate("element => element.parentElement === document.body")

    caixa = menu.bounding_box()
    assert caixa is not None
    assert caixa["x"] >= 0 and caixa["x"] + caixa["width"] <= 1440
    assert caixa["y"] >= 0 and caixa["y"] + caixa["height"] <= 900

    tabela = page.get_by_role("region", name="Assinaturas")
    excesso_vertical = tabela.evaluate("element => element.scrollHeight - element.clientHeight")
    assert excesso_vertical <= 2
    _print(page, "10_menu_acoes_react")
