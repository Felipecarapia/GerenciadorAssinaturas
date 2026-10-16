"""Login com senha única (RF-01 a RF-04).

* A senha fica em st.secrets e é comparada com hmac.compare_digest (RF-02).
* 5 tentativas erradas bloqueiam o acesso por alguns minutos (RF-03). O
  contador fica no servidor, por endereço IP, para não zerar ao recarregar.
* A sessão vive só em st.session_state: fechar a aba ou recarregar a página
  pede a senha de novo (RF-04).
"""
from __future__ import annotations

import base64
import hmac
import threading
import time
from pathlib import Path

import streamlit as st

from servicos import planilha

MAX_TENTATIVAS = 5
BLOQUEIO_SEGUNDOS = 5 * 60
SENHA_DEMO = "demo"
ICONE_LICENZY = Path(__file__).resolve().parent.parent / "assets" / "icone_licenzy.png"


def _icone_licenzy_base64() -> str:
    return base64.b64encode(ICONE_LICENZY.read_bytes()).decode("ascii")


@st.cache_resource
def _controle_tentativas():
    return {"trava": threading.Lock(), "por_ip": {}}


def _ip() -> str:
    try:
        return st.context.ip_address or "desconhecido"
    except Exception:
        return "desconhecido"


def _senha_configurada() -> str | None:
    try:
        senha = st.secrets["app"]["senha"]
        return str(senha) if senha else None
    except Exception:
        return None


def autenticado() -> bool:
    return bool(st.session_state.get("autenticado"))


def sair():
    st.session_state.clear()


def _situacao(ip):
    ctl = _controle_tentativas()
    with ctl["trava"]:
        info = ctl["por_ip"].get(ip, {"erros": 0, "ate": 0.0})
        if info["ate"] and time.time() >= info["ate"]:
            info = {"erros": 0, "ate": 0.0}
            ctl["por_ip"][ip] = info
        return dict(info)


def _registrar_erro(ip):
    ctl = _controle_tentativas()
    with ctl["trava"]:
        info = ctl["por_ip"].setdefault(ip, {"erros": 0, "ate": 0.0})
        info["erros"] += 1
        if info["erros"] >= MAX_TENTATIVAS:
            info["ate"] = time.time() + BLOQUEIO_SEGUNDOS
        return dict(info)


def _zerar(ip):
    ctl = _controle_tentativas()
    with ctl["trava"]:
        ctl["por_ip"].pop(ip, None)


def tela():
    senha_certa = _senha_configurada()
    demo = senha_certa is None and planilha.modo_local()

    _, meio, _ = st.columns([1, 1.4, 1])
    with meio:
        st.html(
            f"<div class='ga-login-brand'>"
            f"<img src='data:image/png;base64,{_icone_licenzy_base64()}' alt='Símbolo da Licenzy'>"
            "<span>Licenzy</span>"
            "</div>"
            "<div class='ga-login-marca'>"
            "<p class='ga-login-owner'>Uma solução do "
            "<strong>Instituto Recôncavo de Tecnologia</strong></p>"
            "<p class='ga-login-desc'>Gestão de assinaturas · Acesso corporativo restrito</p>"
            "</div>"
        )
        if senha_certa is None and not demo:
            st.error("A senha de acesso não está configurada. Defina [app] senha nos Secrets da hospedagem.")
            st.stop()

        ip = _ip()
        info = _situacao(ip)
        if info["ate"]:
            minutos = max(1, round((info["ate"] - time.time()) / 60))
            st.error(f"Muitas tentativas erradas. Tente de novo em cerca de {minutos} minuto(s).",
                     icon=":material/lock_clock:")
            st.stop()

        with st.form("login", border=True):
            senha = st.text_input("Senha", type="password", placeholder="Digite a senha de acesso")
            entrar = st.form_submit_button("Entrar", type="primary", width="stretch",
                                           icon=":material/login:")
        if demo:
            st.info(f"Modo de demonstração: a senha é **{SENHA_DEMO}**. "
                    "Configure [app] senha nos Secrets para trocar.", icon=":material/info:")

        if entrar:
            esperada = senha_certa if senha_certa is not None else SENHA_DEMO
            if hmac.compare_digest(senha.encode("utf-8"), esperada.encode("utf-8")):
                _zerar(ip)
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                info = _registrar_erro(ip)
                restantes = MAX_TENTATIVAS - info["erros"]
                if restantes > 0:
                    st.error(f"Senha incorreta. Restam {restantes} tentativa(s).")
                else:
                    st.rerun()
