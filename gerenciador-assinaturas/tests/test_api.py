from fastapi.testclient import TestClient
import pytest

from api import auth
from api.main import app
from servicos import planilha
from servicos.esquema import ABA_EQUIPE, ABA_FUNCIONARIOS


@pytest.fixture
def cliente(planilha_vazia, monkeypatch):
    monkeypatch.setenv("LICENZY_SESSION_KEY", "chave-segura-exclusiva-dos-testes")
    auth._tentativas.clear()
    with TestClient(app) as c:
        yield c


def login(cliente, perfil="suporte"):
    resposta = cliente.post("/api/login", json={"email": f"{perfil}@reconcavo.org.br", "senha": "demo"})
    assert resposta.status_code == 200, resposta.text
    return resposta


def assinatura(cliente, nome="Figma"):
    resposta = cliente.post("/api/assinaturas", json={"dados": {
        "Nome": nome, "Logo (URL)": "", "Categoria": "Design", "Plano": "Mensal",
        "Valor (R$)": 120, "Vencimento": "2027-01-10", "Status": "Ativa",
    }})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["id"]


def pessoa(cliente, nome="Ana Souza", email="ana@empresa.com.br"):
    resposta = cliente.post("/api/pessoas", json={"dados": {
        "Nome completo": nome, "E-mail": email, "Departamento": "TI", "Cargo": "Analista",
    }})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["id"]


def projeto(cliente, pessoa_id, assinatura_id):
    resposta = cliente.post("/api/projetos", json={
        "dados": {"Nome": "Portal", "Cliente": "IRT", "Responsavel": "Ana", "Departamento": "TI", "Observacoes": ""},
        "equipe": [{"pessoa_id": pessoa_id, "assinaturas_ids": [assinatura_id]}],
    })
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["id"]


def original(cliente, projeto_id):
    resposta = cliente.get(f"/api/projetos/{projeto_id}")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["original"]


def test_rotas_exigem_login(cliente):
    assert cliente.get("/api/projetos").status_code == 401
    assert cliente.get("/api/sessao").status_code == 401


def test_login_individual_sessao_e_logout(cliente):
    login(cliente, "financeiro")
    sessao = cliente.get("/api/sessao")
    assert sessao.json()["usuario"]["perfil"] == "financeiro"
    assert sessao.json()["usuario"]["email"] == "financeiro@reconcavo.org.br"
    assert cliente.post("/api/logout").status_code == 200
    assert cliente.get("/api/sessao").status_code == 401


def test_login_nao_revela_se_email_existe(cliente):
    existente = cliente.post("/api/login", json={"email": "suporte@reconcavo.org.br", "senha": "errada"})
    inexistente = cliente.post("/api/login", json={"email": "ninguem@reconcavo.org.br", "senha": "errada"})
    assert existente.status_code == inexistente.status_code == 401
    assert existente.json()["detail"]["mensagem"] == inexistente.json()["detail"]["mensagem"]


def test_fluxo_aprovacao_e_permissoes(cliente):
    login(cliente)
    assinatura_id = assinatura(cliente)
    ana = pessoa(cliente)
    projeto_id = projeto(cliente, ana, assinatura_id)

    projeto_atual = original(cliente, projeto_id)
    assert projeto_atual["Status"] == "Pendente"
    assert set(planilha.ler_fresco(ABA_EQUIPE)["Situação"]) == {"Proposto"}
    assert cliente.post(f"/api/projetos/{projeto_id}/ativar", json={"original": projeto_atual}).status_code == 403

    cliente.post("/api/logout")
    login(cliente, "financeiro")
    ativado = cliente.post(f"/api/projetos/{projeto_id}/ativar", json={"original": projeto_atual})
    assert ativado.status_code == 200, ativado.text
    assert set(planilha.ler_fresco(ABA_EQUIPE)["Situação"]) == {"Aprovado"}
    assert planilha.ler_registro(ABA_FUNCIONARIOS, ana)["Assinaturas"] == "Figma"


def test_edicao_ativa_preserva_acesso_ate_nova_decisao(cliente):
    login(cliente)
    assinatura_id = assinatura(cliente)
    ana = pessoa(cliente)
    bia = pessoa(cliente, "Bia Lima", "bia@empresa.com.br")
    projeto_id = projeto(cliente, ana, assinatura_id)
    pendente = original(cliente, projeto_id)
    cliente.post("/api/logout"); login(cliente, "financeiro")
    assert cliente.post(f"/api/projetos/{projeto_id}/ativar", json={"original": pendente}).status_code == 200

    cliente.post("/api/logout"); login(cliente)
    ativo = original(cliente, projeto_id)
    edicao = cliente.put(f"/api/projetos/{projeto_id}", json={
        "dados": {"Nome": "Portal", "Cliente": "IRT", "Responsavel": "Bia", "Departamento": "TI", "Observacoes": "troca"},
        "equipe": [{"pessoa_id": bia, "assinaturas_ids": [assinatura_id]}], "original": ativo,
    })
    assert edicao.status_code == 200, edicao.text
    assert edicao.json()["status"] == "Pendente"
    assert set(planilha.ler_fresco(ABA_EQUIPE)["Situação"]) == {"Proposto", "Remoção proposta"}
    assert planilha.ler_registro(ABA_FUNCIONARIOS, ana)["Assinaturas"] == "Figma"
    assert planilha.ler_registro(ABA_FUNCIONARIOS, bia)["Assinaturas"] == ""

    cliente.post("/api/logout"); login(cliente, "financeiro")
    revisao = original(cliente, projeto_id)
    assert cliente.post(f"/api/projetos/{projeto_id}/recusar", json={"original": revisao, "motivo": "Ajustar a composição da equipe"}).status_code == 200
    assert planilha.ler_registro(ABA_FUNCIONARIOS, ana)["Assinaturas"] == "Figma"
    recusado = original(cliente, projeto_id)
    assert cliente.post(f"/api/projetos/{projeto_id}/solicitar-ativacao", json={"original": recusado}).status_code == 200
    reenviado = original(cliente, projeto_id)
    assert cliente.post(f"/api/projetos/{projeto_id}/ativar", json={"original": reenviado}).status_code == 200
    assert planilha.ler_registro(ABA_FUNCIONARIOS, ana)["Assinaturas"] == ""
    assert planilha.ler_registro(ABA_FUNCIONARIOS, bia)["Assinaturas"] == "Figma"


def test_conclusao_definitiva(cliente):
    login(cliente)
    assinatura_id, pessoa_id = assinatura(cliente), pessoa(cliente)
    projeto_id = projeto(cliente, pessoa_id, assinatura_id)
    cliente.post("/api/logout"); login(cliente, "financeiro")
    cliente.post(f"/api/projetos/{projeto_id}/ativar", json={"original": original(cliente, projeto_id)})
    atual = original(cliente, projeto_id)
    assert cliente.post(f"/api/projetos/{projeto_id}/concluir", json={"original": atual}).status_code == 200
    assert set(planilha.ler_fresco(ABA_EQUIPE)["Situação"]) == {"Encerrado"}
    assert planilha.ler_registro(ABA_FUNCIONARIOS, pessoa_id)["Assinaturas"] == ""
    assert cliente.post(f"/api/projetos/{projeto_id}/reabrir", json={}).status_code == 404


def test_bloqueio_por_email_vale_entre_ips(cliente):
    for numero in range(5):
        resposta = cliente.post("/api/login", json={"email": "suporte@reconcavo.org.br", "senha": "errada"},
                                headers={"x-real-ip": f"10.0.0.{numero}"})
        assert resposta.status_code in (401, 429)
    sexta = cliente.post("/api/login", json={"email": "suporte@reconcavo.org.br", "senha": "demo"},
                         headers={"x-real-ip": "10.0.0.99"})
    assert sexta.status_code == 429


def test_suporte_nao_ativa_nem_recusa(cliente):
    login(cliente)
    projeto_id = projeto(cliente, pessoa(cliente), assinatura(cliente))
    atual = original(cliente, projeto_id)
    assert cliente.post(f"/api/projetos/{projeto_id}/ativar", json={"original": atual}).status_code == 403
    recusa = cliente.post(f"/api/projetos/{projeto_id}/recusar", json={"original": atual, "motivo": "Motivo suficientemente longo"})
    assert recusa.status_code == 403
    assert original(cliente, projeto_id)["Status"] == "Pendente"


def test_usuario_desativado_perde_sessao(cliente):
    from servicos.esquema import ABA_USUARIOS
    login(cliente)
    usuarios = planilha.ler_fresco(ABA_USUARIOS)
    suporte = usuarios[usuarios["E-mail"] == "suporte@reconcavo.org.br"].iloc[0]
    planilha.atualizar_campos(ABA_USUARIOS, str(suporte["ID"]), {"Ativo": "Não"})
    planilha.limpar_cache()
    assert cliente.get("/api/sessao").status_code == 401


def test_historico_registra_quem_fez(cliente):
    from servicos.esquema import ABA_HISTORICO
    login(cliente)
    projeto(cliente, pessoa(cliente), assinatura(cliente))
    historico = planilha.ler_fresco(ABA_HISTORICO)
    criado = historico[historico["Evento"] == "Projeto criado"].iloc[0]
    assert criado["Quem"] == "suporte@reconcavo.org.br"


def test_recusa_sem_motivo_e_422(cliente):
    login(cliente)
    projeto_id = projeto(cliente, pessoa(cliente), assinatura(cliente))
    cliente.post("/api/logout"); login(cliente, "financeiro")
    resposta = cliente.post(f"/api/projetos/{projeto_id}/recusar", json={"original": original(cliente, projeto_id), "motivo": "curto"})
    assert resposta.status_code == 422
