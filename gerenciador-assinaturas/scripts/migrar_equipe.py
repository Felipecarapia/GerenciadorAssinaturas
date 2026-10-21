"""Migra os vínculos atuais (pessoa → assinatura e projeto → assinatura) para a
aba ``Equipe do projeto``, sem ninguém perder acesso no dia da troca.

Por padrão roda em simulação e só imprime o relatório. Use ``--aplicar`` para
gravar. Recusa rodar se a aba ``Equipe do projeto`` já tiver linhas, a menos
que receba ``--forcar``. Usa os mesmos segredos do app (modo local ou Sheets).

  python scripts/migrar_equipe.py            # simulação
  python scripts/migrar_equipe.py --aplicar  # grava
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from servicos import planilha  # noqa: E402
from servicos.calculos import normalizar, separar_lista  # noqa: E402
from servicos.cadastros import _evento, agora, registrar  # noqa: E402
from servicos.esquema import (  # noqa: E402
    ABA_ASSINATURAS, ABA_EQUIPE, ABA_FUNCIONARIOS, ABA_PROJETOS, ABA_USOS_PROJETO,
    ABA_USUARIOS, COLUNAS, EQ_APROVADO, EQ_PROPOSTO, EV_MIGRACAO_EQUIPE,
    PROJ_ATIVO, PROJ_CONCLUIDO, PROJ_PENDENTE, PROJ_RECUSADO,
)

NOME_PROVISORIO = "Vínculos anteriores (revisar)"
AUTOR = "migração"


class MigracaoRecusada(Exception):
    """A migração não pode ser aplicada (já rodou ou o resultado divergiria)."""


@dataclass
class Plano:
    momento: str
    projetos_alterados: dict[str, dict] = field(default_factory=dict)
    novos_projetos: list[dict] = field(default_factory=list)
    linhas: list[dict] = field(default_factory=list)
    # Relatório
    linhas_por_projeto: Counter = field(default_factory=Counter)
    provisorios: list[tuple[str, str]] = field(default_factory=list)
    usos_sem_pessoa: list[tuple[str, str]] = field(default_factory=list)
    assinaturas_sem_projeto: list[str] = field(default_factory=list)
    nomes_descartados: list[tuple[str, str]] = field(default_factory=list)
    # Conferência: assinaturas (por nome) de cada pessoa antes e depois
    antes: dict[str, set[str]] = field(default_factory=dict)
    depois: dict[str, set[str]] = field(default_factory=dict)

    def divergencias(self) -> list[str]:
        return [pessoa for pessoa in sorted(set(self.antes) | set(self.depois))
                if self.antes.get(pessoa, set()) != self.depois.get(pessoa, set())]


def _status_migrado(status: object) -> tuple[str, str]:
    """Status novo e a nota para Observações (vazia quando não muda)."""
    valor = normalizar(status)
    if valor in ("", normalizar(PROJ_ATIVO)):
        return PROJ_ATIVO, ""
    if valor == normalizar(PROJ_CONCLUIDO):
        return PROJ_CONCLUIDO, ""
    if valor in (normalizar(PROJ_PENDENTE), normalizar(PROJ_RECUSADO)):
        return str(status), ""
    return PROJ_PENDENTE, f"migrado de {status}"


def _linha(projeto_id: str, pessoa_id: str, assinatura_id: str, situacao: str, momento: str) -> dict:
    return {
        "ID": planilha.novo_id(ABA_EQUIPE), "Projeto ID": projeto_id, "Pessoa ID": pessoa_id,
        "Assinatura ID": assinatura_id, "Situação": situacao, "Proposto por": AUTOR,
        "Proposto em": momento, "Cadastrado em": momento,
    }


def planejar() -> Plano:
    assinaturas = planilha.ler_fresco(ABA_ASSINATURAS)
    pessoas = planilha.ler_fresco(ABA_FUNCIONARIOS)
    projetos = planilha.ler_fresco(ABA_PROJETOS)
    usos = planilha.ler_fresco(ABA_USOS_PROJETO)
    plano = Plano(momento=agora().strftime("%Y-%m-%d %H:%M:%S"))

    ass_por_nome = {normalizar(a["Nome"]): str(a["ID"]) for _, a in assinaturas.iterrows()}
    nome_por_ass = {str(a["ID"]): str(a["Nome"]) for _, a in assinaturas.iterrows()}
    nome_pessoa = {str(p["ID"]): str(p["Nome completo"]) for _, p in pessoas.iterrows()}

    # Acessos de hoje: pares (pessoa, assinatura) da coluna Funcionários.Assinaturas
    pessoas_por_ass: dict[str, set[str]] = defaultdict(set)
    acessos: set[tuple[str, str]] = set()
    for _, pessoa in pessoas.iterrows():
        pessoa_id = str(pessoa["ID"])
        plano.antes[pessoa_id] = set()
        for nome in separar_lista(pessoa.get("Assinaturas")):
            assinatura_id = ass_por_nome.get(normalizar(nome))
            if assinatura_id is None:
                plano.nomes_descartados.append((nome_pessoa[pessoa_id], nome))
                continue
            pessoas_por_ass[assinatura_id].add(pessoa_id)
            acessos.add((pessoa_id, assinatura_id))
            plano.antes[pessoa_id].add(nome_por_ass[assinatura_id])

    # Status dos projetos: Ativo fica Ativo, Pausado vira Pendente, Concluído fica
    status_novo: dict[str, str] = {}
    nome_projeto: dict[str, str] = {}
    for _, projeto in projetos.iterrows():
        projeto_id = str(projeto["ID"])
        nome_projeto[projeto_id] = str(projeto["Nome"])
        status, nota = _status_migrado(projeto.get("Status"))
        status_novo[projeto_id] = status
        campos: dict[str, str] = {}
        if status != str(projeto.get("Status")):
            campos["Status"] = status
        if nota:
            observacoes = str(projeto.get("Observações") or "").strip()
            campos["Observações"] = f"{observacoes} ({nota})".strip() if observacoes else nota
        if status == PROJ_ATIVO and not str(projeto.get("Aprovado em") or "").strip():
            campos |= {"Aprovado por": AUTOR, "Aprovado em": plano.momento}
        if campos:
            plano.projetos_alterados[projeto_id] = campos

    # Equipe: pessoa × assinatura que está ao mesmo tempo na pessoa e no projeto
    cobertos: set[tuple[str, str]] = set()
    vistos: set[tuple[str, str, str]] = set()
    for _, uso in usos.iterrows():
        projeto_id, assinatura_id = str(uso["Projeto ID"]), str(uso["Assinatura ID"])
        status = status_novo.get(projeto_id)
        if status is None or status == PROJ_CONCLUIDO:
            continue
        situacao = EQ_APROVADO if status == PROJ_ATIVO else EQ_PROPOSTO
        pessoas_do_uso = sorted(pessoas_por_ass.get(assinatura_id, set()))
        if not pessoas_do_uso:
            plano.usos_sem_pessoa.append((nome_projeto[projeto_id], nome_por_ass.get(assinatura_id, assinatura_id)))
        for pessoa_id in pessoas_do_uso:
            chave = (projeto_id, pessoa_id, assinatura_id)
            if chave in vistos:
                continue
            vistos.add(chave)
            plano.linhas.append(_linha(projeto_id, pessoa_id, assinatura_id, situacao, plano.momento))
            plano.linhas_por_projeto[nome_projeto[projeto_id]] += 1
            if situacao == EQ_APROVADO:
                cobertos.add((pessoa_id, assinatura_id))

    # O que nenhum projeto Ativo cobre vai para o projeto provisório
    sobras = sorted(acessos - cobertos)
    if sobras:
        projeto_id = planilha.novo_id(ABA_PROJETOS)
        plano.novos_projetos.append({
            "ID": projeto_id, "Nome": NOME_PROVISORIO, "Cliente": "", "Responsável": "",
            "Departamento": "", "Data de início": "", "Data de término": "", "Status": PROJ_ATIVO,
            "Observações": "Criado pela migração. Redistribua as pessoas nos projetos certos e conclua este.",
            "Cadastrado em": plano.momento, "Motivo da recusa": "",
            "Solicitado por": AUTOR, "Solicitado em": plano.momento,
            "Aprovado por": AUTOR, "Aprovado em": plano.momento, "Recusado por": "", "Recusado em": "",
        })
        status_novo[projeto_id] = PROJ_ATIVO
        for pessoa_id, assinatura_id in sobras:
            plano.linhas.append(_linha(projeto_id, pessoa_id, assinatura_id, EQ_APROVADO, plano.momento))
            plano.linhas_por_projeto[NOME_PROVISORIO] += 1
            plano.provisorios.append((nome_pessoa[pessoa_id], nome_por_ass[assinatura_id]))

    # Resultado esperado: o que sincronizar_derivados() vai gravar em cada pessoa
    plano.depois = {pessoa_id: set() for pessoa_id in plano.antes}
    em_projeto_ativo: set[str] = set()
    for linha in plano.linhas:
        if linha["Situação"] == EQ_APROVADO:
            plano.depois[linha["Pessoa ID"]].add(nome_por_ass[linha["Assinatura ID"]])
            em_projeto_ativo.add(linha["Assinatura ID"])
    plano.assinaturas_sem_projeto = sorted(
        str(a["Nome"]) for _, a in assinaturas.iterrows()
        if normalizar(a.get("Status")) == "ativa" and str(a["ID"]) not in em_projeto_ativo
    )
    return plano


def relatorio(plano: Plano) -> str:
    partes = [f"Linhas de equipe a criar: {len(plano.linhas)}"]
    partes += [f"  · {projeto}: {qtd}" for projeto, qtd in sorted(plano.linhas_por_projeto.items())]
    if plano.projetos_alterados:
        partes.append(f"Projetos com status ou aprovação ajustados: {len(plano.projetos_alterados)}")
    partes.append(f"Pares no projeto provisório “{NOME_PROVISORIO}”: {len(plano.provisorios)}")
    partes += [f"  · {pessoa} → {assinatura}" for pessoa, assinatura in plano.provisorios]
    partes.append(f"Projetos sem nenhuma pessoa para a assinatura (o custo do projeto cai): {len(plano.usos_sem_pessoa)}")
    partes += [f"  · {projeto} → {assinatura}" for projeto, assinatura in plano.usos_sem_pessoa]
    partes.append(f"Assinaturas Ativas sem projeto: {len(plano.assinaturas_sem_projeto)}")
    partes += [f"  · {nome}" for nome in plano.assinaturas_sem_projeto]
    if plano.nomes_descartados:
        partes.append(f"Nomes em Funcionários.Assinaturas que não existem como assinatura (serão descartados): {len(plano.nomes_descartados)}")
        partes += [f"  · {pessoa} → {nome}" for pessoa, nome in plano.nomes_descartados]
    return "\n".join(partes)


def _preparar_abas() -> None:
    """Cabeçalhos novos no fim de Projetos e abas novas (criadas na leitura)."""
    planilha.motor().atualizar_linhas(ABA_PROJETOS, {1: COLUNAS[ABA_PROJETOS]})
    planilha.ler_fresco(ABA_EQUIPE)
    planilha.ler_fresco(ABA_USUARIOS)
    planilha.limpar_cache()


def migrar(aplicar: bool = False, forcar: bool = False) -> Plano:
    if not planilha.ler_fresco(ABA_EQUIPE).empty and not forcar:
        raise MigracaoRecusada("A aba Equipe do projeto já tem linhas. Use --forcar só depois de conferir um backup.")
    plano = planejar()
    divergentes = plano.divergencias()
    if divergentes:
        raise MigracaoRecusada("A migração mudaria as assinaturas de: " + ", ".join(divergentes))
    if not aplicar:
        return plano

    from servicos.projetos import sincronizar_derivados

    _preparar_abas()
    for projeto_id, campos in plano.projetos_alterados.items():
        planilha.atualizar_campos(ABA_PROJETOS, projeto_id, campos)
    if plano.novos_projetos:
        planilha.inserir(ABA_PROJETOS, plano.novos_projetos)
    if plano.linhas:
        planilha.inserir(ABA_EQUIPE, plano.linhas)
    planilha.limpar_cache()
    sincronizar_derivados(permitir_equipe_vazia=True)

    pessoas = planilha.ler_fresco(ABA_FUNCIONARIOS)
    gravado = {str(p["ID"]): set(separar_lista(p.get("Assinaturas"))) for _, p in pessoas.iterrows()}
    diferentes = [pid for pid in plano.depois if gravado.get(pid, set()) != plano.depois[pid]]
    if diferentes:
        raise MigracaoRecusada("Funcionários.Assinaturas ficou diferente do esperado para: " + ", ".join(diferentes))
    registrar([_evento("", EV_MIGRACAO_EQUIPE, "Equipe do projeto", "", f"{len(plano.linhas)} linhas")])
    planilha.limpar_cache()
    return plano


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--aplicar", action="store_true", help="Grava a migração (sem ele, só simula).")
    parser.add_argument("--forcar", action="store_true", help="Roda mesmo se Equipe do projeto já tiver linhas.")
    args = parser.parse_args()
    try:
        plano = migrar(aplicar=args.aplicar, forcar=args.forcar)
    except MigracaoRecusada as exc:
        raise SystemExit(f"Migração não aplicada: {exc}") from exc
    print(relatorio(plano))
    if args.aplicar:
        print("\nMigração concluída. Agora rode scripts/criar_usuarios.py.")
    else:
        print("\nSimulação concluída; nada foi alterado. Rode de novo com --aplicar para gravar.")


if __name__ == "__main__":
    main()
