"""Dados fictícios: 20 assinaturas e 15 pessoas, com histórico de 12 meses.

Usado pelo botão "Carregar dados de exemplo" (modo local) e pelo script
scripts/dados_exemplo.py (planilha de testes). Nunca rode nos dados reais.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from servicos import planilha
from servicos.calculos import formatar_reais, juntar_lista
from servicos.esquema import (
    ABA_ASSINATURAS, ABA_EQUIPE, ABA_FUNCIONARIOS, ABA_HISTORICO, ABA_PROJETOS,
    EQ_APROVADO, EQ_PROPOSTO, EV_CRIADA, EV_PLANO, EV_STATUS, EV_VALOR,
    PROJ_ATIVO, PROJ_PENDENTE, PROJ_RECUSADO,
)


def _logo(dominio):
    return f"https://www.google.com/s2/favicons?domain={dominio}&sz=64"


# nome, domínio do logo, categoria, plano, valor, dias até vencer, status, meses desde o cadastro
ASSINATURAS = [
    ("Adobe Creative Cloud", "adobe.com", "Design", "Anual", 4500.00, 45, "Ativa", 14),
    ("Figma", "figma.com", "Design", "Mensal", 220.00, 6, "Ativa", 13),
    ("Canva Pro", "canva.com", "Design", "Anual", 289.90, 120, "Ativa", 10),
    ("Microsoft 365", "microsoft.com", "Produtividade", "Anual", 3600.00, 210, "Ativa", 15),
    ("Google Workspace", "workspace.google.com", "Produtividade", "Mensal", 980.00, 12, "Ativa", 15),
    ("Notion", "notion.so", "Produtividade", "Mensal", 180.00, 3, "Ativa", 9),
    ("Slack", "slack.com", "Comunicação", "Mensal", 450.00, 18, "Ativa", 12),
    ("Zoom", "zoom.us", "Comunicação", "Mensal", 160.00, -2, "Ativa", 11),
    ("GitHub", "github.com", "Desenvolvimento", "Mensal", 210.00, 22, "Ativa", 14),
    ("JetBrains", "jetbrains.com", "Desenvolvimento", "Anual", 2900.00, 75, "Ativa", 8),
    ("Postman", "postman.com", "Desenvolvimento", "Mensal", 75.00, 9, "Em teste", 1),
    ("Dropbox", "dropbox.com", "Armazenamento", "Anual", 1450.00, 160, "Ativa", 13),
    ("Backblaze", "backblaze.com", "Armazenamento", "Mensal", 60.00, 27, "Ativa", 6),
    ("1Password", "1password.com", "Segurança", "Anual", 890.00, 33, "Ativa", 7),
    ("Bitdefender", "bitdefender.com", "Segurança", "Anual", 1200.00, 95, "Pausada", 12),
    ("RD Station", "rdstation.com", "Marketing", "Mensal", 650.00, 14, "Ativa", 5),
    ("Mailchimp", "mailchimp.com", "Marketing", "Mensal", 300.00, 40, "Cancelada", 14),
    ("Semrush", "semrush.com", "Marketing", "Mensal", 700.00, 52, "Ativa", 4),
    ("Conta Azul", "contaazul.com", "Financeiro", "Mensal", 290.00, 1, "Ativa", 10),
    ("Sublime Text", "sublimetext.com", "Desenvolvimento", "Vitalício", 520.00, None, "Ativa", 12),
]

# alterações passadas: (assinatura, meses atrás, campo, anterior, evento)
ALTERACOES = [
    ("Google Workspace", 4, "Valor (R$)", "840.00", EV_VALOR),
    ("Slack", 6, "Valor (R$)", "380.00", EV_VALOR),
    ("Figma", 3, "Plano", "Anual", EV_PLANO),
    ("Figma", 3, "Valor (R$)", "2160.00", EV_VALOR),
    ("Mailchimp", 2, "Status", "Ativa", EV_STATUS),
    ("Bitdefender", 1, "Status", "Ativa", EV_STATUS),
    ("Adobe Creative Cloud", 7, "Valor (R$)", "3900.00", EV_VALOR),
]

PESSOAS = [
    ("Ana Beatriz Souza", "Marketing", "Coordenadora de Marketing",
     ["Canva Pro", "RD Station", "Semrush", "Slack", "Google Workspace"]),
    ("Bruno Carvalho Lima", "TI", "Desenvolvedor",
     ["GitHub", "JetBrains", "Postman", "Slack", "Sublime Text", "Google Workspace"]),
    ("Camila Ferreira", "Comercial", "Executiva de Contas", ["Zoom", "Slack", "Google Workspace"]),
    ("Daniel Rocha", "TI", "Analista de Infraestrutura",
     ["Backblaze", "1Password", "Bitdefender", "GitHub", "Google Workspace"]),
    ("Eduarda Nascimento", "Marketing", "Designer",
     ["Adobe Creative Cloud", "Figma", "Canva Pro", "Google Workspace"]),
    ("Felipe Andrade", "Financeiro", "Analista Financeiro", ["Conta Azul", "Microsoft 365", "Google Workspace"]),
    ("Gabriela Martins", "Pedagógico", "Coordenadora Pedagógica",
     ["Zoom", "Notion", "Microsoft 365", "Google Workspace"]),
    ("Henrique Barbosa", "Administrativo", "Gerente Administrativo",
     ["Microsoft 365", "Dropbox", "Slack", "Google Workspace"]),
    ("Isabela Ribeiro", "Recursos Humanos", "Analista de RH", ["Notion", "Zoom", "Google Workspace"]),
    ("João Pedro Alves", "TI", "Coordenador de TI",
     ["1Password", "GitHub", "Microsoft 365", "Slack", "Google Workspace"]),
    ("Larissa Gomes", "Marketing", "Analista de Conteúdo",
     ["Canva Pro", "Mailchimp", "Notion", "Google Workspace"]),
    ("Marcelo Teixeira", "Comercial", "Gerente Comercial",
     ["RD Station", "Zoom", "Microsoft 365", "Google Workspace"]),
    ("Natália Pires", "Financeiro", "Controller", ["Conta Azul", "Dropbox", "Google Workspace"]),
    ("Otávio Mendes", "Pedagógico", "Professor", ["Zoom", "Canva Pro", "Google Workspace"]),
    ("Paula Cristina Dias", "Administrativo", "Assistente Administrativa",
     ["Dropbox", "Notion", "Google Workspace"]),
]


def _email(nome):
    import unicodedata
    base = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower().split()
    return f"{base[0]}.{base[-1]}@empresa.com.br"


def carregar(agora: datetime, com_pendencias: bool = False) -> None:
    rnd = random.Random(42)
    hoje = agora.date()
    reg_ass, hist = [], []
    cadastro = {}
    for nome, dom, cat, plano, valor, dias, status, meses in ASSINATURAS:
        cad = agora - timedelta(days=meses * 30 + rnd.randint(0, 20))
        cadastro[nome] = cad
        reg_ass.append({
            "ID": planilha.novo_id(ABA_ASSINATURAS), "Nome": nome, "Logo (URL)": _logo(dom),
            "Categoria": cat, "Plano": plano, "Valor (R$)": valor,
            "Vencimento": "" if dias is None else (hoje + timedelta(days=dias)).isoformat(),
            "Status": status, "Cadastrado em": cad.strftime("%Y-%m-%d %H:%M:%S"),
        })
    # valor/plano/status originais na criação = desfazer as alterações
    originais = {a["Nome"]: dict(a) for a in reg_ass}
    for nome, _m, campo, anterior, _ev in ALTERACOES:
        originais[nome][campo] = anterior
    for a in reg_ass:
        o = originais[a["Nome"]]
        hist.append(_hist(cadastro[a["Nome"]], a["Nome"], EV_CRIADA, "", "",
                          f"{o['Plano']} · {formatar_reais(float(o['Valor (R$)']))} · {o['Status']}", "app"))
    for nome, meses, campo, anterior, ev in ALTERACOES:
        atual = next(a for a in reg_ass if a["Nome"] == nome)[campo]
        novo = f"{float(atual):.2f}" if campo == "Valor (R$)" else atual
        quando = agora - timedelta(days=meses * 30 - rnd.randint(0, 10))
        hist.append(_hist(quando, nome, ev, campo, anterior, novo, rnd.choice(["app", "planilha"])))

    reg_func = []
    for nome, dep, cargo, assin in PESSOAS:
        cad = agora - timedelta(days=rnd.randint(30, 400))
        reg_func.append({
            "ID": planilha.novo_id(ABA_FUNCIONARIOS), "Nome completo": nome, "E-mail": _email(nome),
            "Departamento": dep, "Cargo": cargo, "Assinaturas": "",
            "Cadastrado em": cad.strftime("%Y-%m-%d %H:%M:%S"),
        })

    if com_pendencias:
        reg_func.append({
            "ID": planilha.novo_id(ABA_FUNCIONARIOS), "Nome completo": "Rafael Exemplo",
            "E-mail": "camila.ferreira@empresa.com.br", "Departamento": "Comercial",
            "Cargo": "Estagiário", "Assinaturas": "Zoom, Trello",
            "Cadastrado em": agora.strftime("%Y-%m-%d %H:%M:%S"),
        })
        reg_ass.append({
            "ID": planilha.novo_id(ABA_ASSINATURAS), "Nome": "Licença sem valor",
            "Logo (URL)": "", "Categoria": "Outros", "Plano": "Mensal", "Valor (R$)": "",
            "Vencimento": "", "Status": "Ativa", "Cadastrado em": agora.strftime("%Y-%m-%d %H:%M:%S"),
        })

    hist.sort(key=lambda h: h["Data e hora"])
    planilha.inserir(ABA_ASSINATURAS, reg_ass)
    planilha.inserir(ABA_FUNCIONARIOS, reg_func)
    planilha.inserir(ABA_HISTORICO, hist)
    _criar_projetos_exemplo(reg_ass, reg_func, agora)
    from servicos.projetos import sincronizar_derivados
    sincronizar_derivados()
    planilha.limpar_cache()


def _criar_projetos_exemplo(assinaturas: list[dict], pessoas: list[dict], momento: datetime) -> None:
    ass_por_nome = {a["Nome"]: a["ID"] for a in assinaturas}
    configuracoes = [
        ("Plataforma educacional", "IRT", PROJ_ATIVO, range(0, 5)),
        ("Operação corporativa", "Interno", PROJ_ATIVO, range(5, 10)),
        ("Marketing 360", "Institucional", PROJ_ATIVO, range(10, 15)),
        ("Portal do cliente", "Cliente piloto", PROJ_PENDENTE, (0, 1, 5)),
        ("Laboratório de dados", "Pesquisa", PROJ_RECUSADO, (2, 3)),
    ]
    projetos, equipe = [], []
    texto = momento.strftime("%Y-%m-%d %H:%M:%S")
    for nome, cliente, status, indices in configuracoes:
        projeto_id = planilha.novo_id(ABA_PROJETOS)
        projetos.append({
            "ID": projeto_id, "Nome": nome, "Cliente": cliente, "Responsável": "Equipe Licenzy",
            "Departamento": "TI", "Data de início": momento.date().isoformat(), "Data de término": "",
            "Status": status, "Observações": "Dados de demonstração", "Cadastrado em": texto,
            "Motivo da recusa": "Revisar o escopo e o custo previsto." if status == PROJ_RECUSADO else "",
            "Solicitado por": "suporte@reconcavo.org.br", "Solicitado em": texto,
            "Aprovado por": "financeiro@reconcavo.org.br" if status == PROJ_ATIVO else "",
            "Aprovado em": texto if status == PROJ_ATIVO else "",
            "Recusado por": "financeiro@reconcavo.org.br" if status == PROJ_RECUSADO else "",
            "Recusado em": texto if status == PROJ_RECUSADO else "",
        })
        situacao = EQ_APROVADO if status == PROJ_ATIVO else EQ_PROPOSTO
        for indice in indices:
            pessoa = pessoas[indice]
            nomes = PESSOAS[indice][3][:2]
            for assinatura_nome in nomes:
                assinatura_id = ass_por_nome.get(assinatura_nome)
                if assinatura_id:
                    equipe.append({
                        "ID": planilha.novo_id(ABA_EQUIPE), "Projeto ID": projeto_id,
                        "Pessoa ID": pessoa["ID"], "Assinatura ID": assinatura_id,
                        "Situação": situacao, "Proposto por": "dados de exemplo",
                        "Proposto em": texto, "Cadastrado em": texto,
                    })
    planilha.inserir(ABA_PROJETOS, projetos)
    planilha.inserir(ABA_EQUIPE, equipe)


def _hist(quando, assinatura, evento, campo, anterior, novo, origem):
    return {
        "Data e hora": quando.strftime("%Y-%m-%d %H:%M:%S"),
        "Origem": origem, "Quem": "dados de exemplo" if origem == "app" else "equipe@empresa.com.br",
        "Assinatura": assinatura, "Evento": evento, "Campo": campo,
        "Valor anterior": anterior, "Valor novo": novo,
    }
