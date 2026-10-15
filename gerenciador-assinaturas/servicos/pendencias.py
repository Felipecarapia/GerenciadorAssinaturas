"""Painel de Pendências (RF-25): problemas de dados na planilha."""
from __future__ import annotations

from collections import Counter

import pandas as pd

from servicos.calculos import (
    email_valido, meses_do_plano, normalizar, para_data, para_numero, separar_lista, vazio,
)
from servicos.esquema import ABA_ASSINATURAS, ABA_FUNCIONARIOS

# tipos de pendência
T_INEXISTENTE = "Assinatura escolhida não existe"
T_OBRIGATORIO = "Campo obrigatório vazio"
T_VALOR = "Valor inválido"
T_DATA = "Data inválida"
T_EMAIL_DUP = "E-mail duplicado"
T_EMAIL_INV = "E-mail inválido"
T_NOME_DUP = "Nome de assinatura duplicado"
T_VIRGULA = "Nome com vírgula"
T_FORA_LISTA = "Opção fora da lista"


def _p(aba, linha, id_, tipo, descricao, item):
    return {"Aba": aba, "Linha": int(linha), "ID": str(id_), "Tipo": tipo,
            "Descrição": descricao, "Item": item}


def listar(df_ass: pd.DataFrame, df_func: pd.DataFrame, listas: dict[str, list[str]]) -> pd.DataFrame:
    p = []
    nomes_validos = set()
    if not df_ass.empty:
        contagem = Counter(normalizar(n) for n in df_ass["Nome"] if not vazio(n))
        opcoes = {"Categoria": listas.get("Categorias", []), "Plano": listas.get("Planos", []),
                  "Status": listas.get("Status", [])}
        for _, a in df_ass.iterrows():
            nome = "" if vazio(a["Nome"]) else str(a["Nome"]).strip()
            item = nome or f"(linha {a['_linha']})"
            args = (ABA_ASSINATURAS, a["_linha"], a["ID"])
            if nome:
                nomes_validos.add(nome)
            for campo in ("Nome", "Categoria", "Plano", "Status", "Valor (R$)"):
                if vazio(a[campo]):
                    p.append(_p(*args, T_OBRIGATORIO, f"A coluna {campo} está vazia.", item))
            if nome and "," in nome:
                p.append(_p(*args, T_VIRGULA, "O nome tem vírgula e quebra a lista de múltipla escolha.", item))
            if nome and contagem[normalizar(nome)] > 1:
                p.append(_p(*args, T_NOME_DUP, f"Há mais de uma assinatura chamada “{nome}”.", item))
            if not vazio(a["Valor (R$)"]):
                v = para_numero(a["Valor (R$)"])
                if v is None or v <= 0:
                    p.append(_p(*args, T_VALOR, f"Valor “{a['Valor (R$)']}” não é um número positivo.", item))
            vitalicio = meses_do_plano(a["Plano"]) is None
            if vazio(a["Vencimento"]):
                if not vitalicio and not vazio(a["Plano"]):
                    p.append(_p(*args, T_OBRIGATORIO, "A coluna Vencimento está vazia.", item))
            elif para_data(a["Vencimento"]) is None:
                p.append(_p(*args, T_DATA, f"Vencimento “{a['Vencimento']}” não é uma data.", item))
            for campo, validas in opcoes.items():
                if not vazio(a[campo]) and validas and str(a[campo]).strip() not in validas:
                    p.append(_p(*args, T_FORA_LISTA,
                                f"{campo} “{a[campo]}” não está na aba Listas.", item))

    if not df_func.empty:
        emails = Counter(str(e).strip().casefold() for e in df_func["E-mail"] if not vazio(e))
        deps = listas.get("Departamentos", [])
        for _, f in df_func.iterrows():
            nome = "" if vazio(f["Nome completo"]) else str(f["Nome completo"]).strip()
            item = nome or f"(linha {f['_linha']})"
            args = (ABA_FUNCIONARIOS, f["_linha"], f["ID"])
            for campo in ("Nome completo", "E-mail", "Departamento"):
                if vazio(f[campo]):
                    p.append(_p(*args, T_OBRIGATORIO, f"A coluna {campo} está vazia.", item))
            email = "" if vazio(f["E-mail"]) else str(f["E-mail"]).strip()
            if email and not email_valido(email):
                p.append(_p(*args, T_EMAIL_INV, f"E-mail “{email}” é inválido.", item))
            if email and emails[email.casefold()] > 1:
                p.append(_p(*args, T_EMAIL_DUP, f"O e-mail {email} aparece em mais de uma pessoa.", item))
            if not vazio(f["Departamento"]) and deps and str(f["Departamento"]).strip() not in deps:
                p.append(_p(*args, T_FORA_LISTA, f"Departamento “{f['Departamento']}” não está na aba Listas.", item))
            invalidas = [n for n in separar_lista(f["Assinaturas"]) if n not in nomes_validos]
            if invalidas:
                p.append(_p(*args, T_INEXISTENTE,
                            "Escolha(s) que não existem mais: " + ", ".join(invalidas), item))

    return pd.DataFrame(p, columns=["Aba", "Linha", "ID", "Tipo", "Descrição", "Item"])
