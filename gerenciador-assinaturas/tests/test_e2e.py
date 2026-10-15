"""Teste de ponta a ponta no navegador (Playwright).

Sobe o app numa porta própria, contra uma planilha LOCAL de testes preenchida
com os dados de exemplo (nunca toca na planilha real), e percorre as telas.

    pip install -r requirements-dev.txt
    playwright install chromium
    pytest tests/test_e2e.py

Defina GA_PRINTS=pasta para salvar capturas de tela de cada página.
"""
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
PRINTS = os.environ.get("GA_PRINTS")


def _porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def servidor(tmp_path_factory):
    caminho = tmp_path_factory.mktemp("e2e") / "planilha_e2e.xlsx"
    env = {**os.environ, "GA_PLANILHA_LOCAL": str(caminho), "GA_FORCAR_LOCAL": "1"}
    # preenche a planilha de testes
    subprocess.run([sys.executable, "-c",
                    "from datetime import datetime; from servicos import exemplo; "
                    "exemplo.carregar(datetime.now().replace(microsecond=0), com_pendencias=True)"],
                   cwd=RAIZ, env=env, check=True, capture_output=True)
    porta = _porta_livre()
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true",
         "--server.port", str(porta), "--server.fileWatcherType", "none"],
        cwd=RAIZ, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://localhost:{porta}"
    for _ in range(60):
        try:
            import urllib.request
            if urllib.request.urlopen(url + "/_stcore/health", timeout=1).read() == b"ok":
                break
        except Exception:
            time.sleep(0.5)
    yield url
    proc.terminate()
    proc.wait(10)


def _print(page, nome):
    if PRINTS:
        Path(PRINTS).mkdir(parents=True, exist_ok=True)
        page.wait_for_timeout(3500)
        page.screenshot(path=str(Path(PRINTS) / f"{nome}.png"), full_page=True)


def _entrar(page, url):
    page.goto(url)
    page.get_by_label("Senha").fill("demo")
    page.get_by_role("button", name="Entrar").click()
    expect(page.get_by_role("heading", name="Dashboard")).to_be_visible(timeout=20000)


def test_login_recusa_senha_errada(servidor, page):
    page.goto(servidor)
    page.get_by_label("Senha").fill("errada")
    page.get_by_role("button", name="Entrar").click()
    expect(page.get_by_text("Senha incorreta")).to_be_visible()
    _print(page, "00_login")


def test_percorre_telas(servidor, page):
    page.set_viewport_size({"width": 1440, "height": 1000})
    _entrar(page, servidor)
    expect(page.get_by_text("Gasto mensal").first).to_be_visible()
    expect(page.get_by_text("Alertas de vencimento")).to_be_visible()
    _print(page, "01_dashboard")

    for titulo, arquivo in [("Assinaturas", "02_assinaturas"), ("Pessoas", "03_pessoas"),
                            ("Relatórios", "04_relatorios"), ("Histórico", "05_historico")]:
        page.get_by_role("link", name=titulo).first.click()
        expect(page.get_by_role("heading", name=titulo)).to_be_visible(timeout=20000)
        _print(page, arquivo)

    page.get_by_role("link", name="Pendências").first.click()
    expect(page.get_by_text("pendência(s) encontrada(s)")).to_be_visible(timeout=20000)
    _print(page, "06_pendencias")


def test_cadastrar_assinatura_pela_janela(servidor, page):
    page.set_viewport_size({"width": 1440, "height": 1000})
    _entrar(page, servidor)
    page.get_by_role("link", name="Assinaturas").first.click()
    page.get_by_role("button", name="Nova assinatura").click()
    janela = page.get_by_role("dialog")
    expect(janela).to_be_visible()
    # salvar vazio mostra os erros ao lado dos campos
    janela.get_by_role("button", name="Salvar").click()
    expect(janela.get_by_text("Informe o nome.")).to_be_visible()
    _print(page, "07_validacao")

    nome = f"Teste E2E {datetime.now():%H%M%S}"
    janela.get_by_label("Nome *").fill(nome)
    for rotulo, opcao in [("Categoria *", "Design"), ("Plano *", "Mensal")]:
        janela.get_by_label(rotulo).click()
        page.get_by_role("option", name=opcao, exact=True).click()
    janela.get_by_label("Valor (R$) *").fill("99.90")
    janela.get_by_role("spinbutton", name="day, Vencimento").click()
    page.keyboard.type("01122030")
    janela.get_by_label("Usuários * (mínimo 1)").click()
    page.get_by_role("option").first.click()
    page.keyboard.press("Escape")
    janela.get_by_role("button", name="Salvar").click()
    expect(page.get_by_text(f"Assinatura “{nome}” salva.")).to_be_visible(timeout=20000)


def test_celular(servidor, page):
    page.set_viewport_size({"width": 390, "height": 844})
    _entrar(page, servidor)
    expect(page.get_by_text("Gasto mensal").first).to_be_visible()
    _print(page, "08_celular")
