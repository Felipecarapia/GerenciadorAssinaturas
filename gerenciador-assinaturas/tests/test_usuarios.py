from servicos import planilha, usuarios
from servicos.esquema import ABA_USUARIOS


def test_hash_nao_armazena_senha_e_login_confere(planilha_vazia):
    id_ = usuarios.salvar_usuario("Gestora", "gestora@empresa.com.br", "financeiro", "senha-muito-segura")
    registro = planilha.ler_registro(ABA_USUARIOS, id_)
    assert registro["Senha (hash)"] != "senha-muito-segura"
    assert usuarios.conferir("senha-muito-segura", registro["Senha (hash)"])
    assert not usuarios.conferir("outra-senha", registro["Senha (hash)"])
    assert usuarios.buscar_por_email("GESTORA@empresa.com.br")["ID"] == id_


def test_perfil_e_senha_sao_validados(planilha_vazia):
    import pytest
    with pytest.raises(ValueError):
        usuarios.salvar_usuario("X", "x@empresa.com.br", "admin", "senha-muito-segura")
    with pytest.raises(ValueError):
        usuarios.salvar_usuario("X", "x@empresa.com.br", "suporte", "curta")


def test_hash_malformado_nao_lanca_excecao():
    for guardado in ("", "texto-qualquer", "scrypt$x$8$1$abc$def", "bcrypt$1$2$3$4$5"):
        assert usuarios.conferir("qualquer", guardado) is False
