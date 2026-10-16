"""Estrutura da planilha: nomes das abas, colunas e valores padrão das listas."""

ABA_ASSINATURAS = "Assinaturas"
ABA_FUNCIONARIOS = "Funcionários"
ABA_HISTORICO = "Histórico"
ABA_LISTAS = "Listas"
ABA_PROJETOS = "Projetos"
ABA_USOS_PROJETO = "Uso por projeto"

COLUNAS = {
    ABA_ASSINATURAS: [
        "ID", "Nome", "Logo (URL)", "Categoria", "Plano", "Valor (R$)",
        "Vencimento", "Status", "Cadastrado em",
    ],
    ABA_FUNCIONARIOS: [
        "ID", "Nome completo", "E-mail", "Departamento", "Cargo",
        "Assinaturas", "Cadastrado em",
    ],
    ABA_HISTORICO: [
        "Data e hora", "Origem", "Quem", "Assinatura", "Evento", "Campo",
        "Valor anterior", "Valor novo",
    ],
    ABA_LISTAS: ["Categorias", "Departamentos", "Planos", "Status"],
    ABA_PROJETOS: [
        "ID", "Nome", "Cliente", "Responsável", "Departamento", "Data de início",
        "Data de término", "Status", "Observações", "Cadastrado em",
    ],
    ABA_USOS_PROJETO: [
        "ID", "Projeto ID", "Assinatura ID", "Finalidade", "Responsável",
        "Data de início", "Data de término", "Status", "Observações", "Cadastrado em",
    ],
}

# Abas que têm coluna ID (o app encontra a linha certa por ela)
ABAS_COM_ID = (ABA_ASSINATURAS, ABA_FUNCIONARIOS, ABA_PROJETOS, ABA_USOS_PROJETO)

LISTAS_PADRAO = {
    "Categorias": [
        "Design", "Desenvolvimento", "Produtividade", "Comunicação",
        "Armazenamento", "Segurança", "Marketing", "Financeiro", "Outros",
    ],
    "Departamentos": [
        "Administrativo", "Comercial", "Financeiro", "Marketing",
        "Pedagógico", "Recursos Humanos", "TI",
    ],
    "Planos": ["Mensal", "Trimestral", "Semestral", "Anual", "Vitalício"],
    "Status": ["Ativa", "Em teste", "Pausada", "Cancelada"],
}

# Quantos meses cada plano cobre (para o gasto mensal). Vitalício não entra.
MESES_POR_PLANO = {
    "mensal": 1,
    "trimestral": 3,
    "semestral": 6,
    "anual": 12,
    "vitalício": None,
    "vitalicio": None,
}

STATUS_ATIVO = "Ativa"

# Eventos do Histórico (RF-22) + exclusão
EV_CRIADA = "Assinatura criada"
EV_VALOR = "Valor alterado"
EV_PLANO = "Plano alterado"
EV_STATUS = "Status alterado"
EV_VINCULADO = "Usuário vinculado"
EV_DESVINCULADO = "Usuário desvinculado"
EV_EXCLUIDA = "Assinatura excluída"
EV_RENOMEADA = "Assinatura renomeada"
EV_PAGAMENTO = "Pagamento registrado"
EV_PROJETO_CRIADO = "Projeto criado"
EV_PROJETO_ALTERADO = "Projeto alterado"
EV_PROJETO_EXCLUIDO = "Projeto excluído"
EV_PROJETO_CONCLUIDO = "Projeto concluído"
EV_PROJETO_VINCULADO = "Assinatura vinculada ao projeto"
EV_PROJETO_DESVINCULADO = "Assinatura removida do projeto"

EVENTOS = [
    EV_CRIADA, EV_VALOR, EV_PLANO, EV_STATUS, EV_VINCULADO,
    EV_DESVINCULADO, EV_RENOMEADA, EV_EXCLUIDA, EV_PAGAMENTO,
    EV_PROJETO_CRIADO, EV_PROJETO_ALTERADO, EV_PROJETO_EXCLUIDO, EV_PROJETO_CONCLUIDO,
    EV_PROJETO_VINCULADO, EV_PROJETO_DESVINCULADO,
]

# Campo da assinatura -> evento registrado quando ele muda
EVENTO_POR_CAMPO = {
    "Valor (R$)": EV_VALOR,
    "Plano": EV_PLANO,
    "Status": EV_STATUS,
    "Nome": EV_RENOMEADA,
}
