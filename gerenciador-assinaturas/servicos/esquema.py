"""Estrutura da planilha: nomes das abas, colunas e valores padrão das listas."""

ABA_ASSINATURAS = "Assinaturas"
ABA_FUNCIONARIOS = "Funcionários"
ABA_HISTORICO = "Histórico"
ABA_LISTAS = "Listas"

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
}

# Abas que têm coluna ID (o app encontra a linha certa por ela)
ABAS_COM_ID = (ABA_ASSINATURAS, ABA_FUNCIONARIOS)

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

EVENTOS = [
    EV_CRIADA, EV_VALOR, EV_PLANO, EV_STATUS, EV_VINCULADO,
    EV_DESVINCULADO, EV_RENOMEADA, EV_EXCLUIDA,
]

# Campo da assinatura -> evento registrado quando ele muda
EVENTO_POR_CAMPO = {
    "Valor (R$)": EV_VALOR,
    "Plano": EV_PLANO,
    "Status": EV_STATUS,
    "Nome": EV_RENOMEADA,
}
