"""Regras de negócio: conversões, gasto mensal, alertas e agregações.

Módulo puro (sem Streamlit), para ser testado com pytest.
"""
from __future__ import annotations

import calendar
import math
import re
from datetime import date, datetime, timedelta

import pandas as pd

from servicos.esquema import (
    EV_RENOMEADA, MESES_POR_PLANO, STATUS_ATIVO,
)

# --------------------------------------------------------------------------
# Conversões tolerantes (a planilha pode ter qualquer coisa digitada)
# --------------------------------------------------------------------------
_EPOCA_SHEETS = datetime(1899, 12, 30)


def vazio(v) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    try:
        if pd.isna(v):
            return True
    except (TypeError, ValueError):
        pass
    return str(v).strip() == ""


def para_numero(v) -> float | None:
    """Converte 49.9, '49,90', 'R$ 1.234,56' ou '1234.56' em float. None se inválido."""
    if vazio(v) or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    texto = str(v).strip().replace("R$", "").replace(" ", "").replace(" ", "")
    if not texto:
        return None
    if "," in texto:  # formato brasileiro: 1.234,56
        texto = texto.replace(".", "").replace(",", ".")
    elif texto.count(".") > 1:  # 1.234.567
        texto = texto.replace(".", "")
    try:
        numero = float(texto)
    except ValueError:
        return None
    return None if math.isnan(numero) or math.isinf(numero) else numero


def para_datahora(v) -> datetime | None:
    if vazio(v) or isinstance(v, bool):
        return None
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)
    if isinstance(v, (int, float)):
        # número de série do Google Sheets (dias desde 30/12/1899)
        if 1 <= v <= 2958465:
            return _EPOCA_SHEETS + timedelta(days=float(v))
        return None
    texto = str(v).strip()
    formatos = (
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%d/%m/%y",
    )
    for fmt in formatos:
        try:
            return datetime.strptime(texto, fmt)
        except ValueError:
            continue
    return None


def para_data(v) -> date | None:
    dh = para_datahora(v)
    return dh.date() if dh else None


def separar_lista(v) -> list[str]:
    """'Adobe, Figma' -> ['Adobe', 'Figma'] (como o Sheets guarda a múltipla escolha)."""
    if vazio(v):
        return []
    return [p.strip() for p in str(v).split(",") if p.strip()]


def juntar_lista(itens) -> str:
    vistos = []
    for item in itens:
        item = str(item).strip()
        if item and item not in vistos:
            vistos.append(item)
    return ", ".join(vistos)


def formatar_reais(v) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    texto = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def formatar_data(d) -> str:
    d = para_data(d) if not isinstance(d, date) else d
    return d.strftime("%d/%m/%Y") if d else "—"


# --------------------------------------------------------------------------
# Validações
# --------------------------------------------------------------------------
_EMAIL = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def email_valido(email: str) -> bool:
    return bool(_EMAIL.match(str(email or "").strip()))


def normalizar(texto) -> str:
    return " ".join(str(texto or "").split()).casefold()


# --------------------------------------------------------------------------
# Gasto e alertas (RF-06 e RF-08)
# --------------------------------------------------------------------------
def meses_do_plano(plano) -> int | None:
    """Meses cobertos por um pagamento. None = vitalício (não entra no gasto)."""
    chave = normalizar(plano)
    if chave in MESES_POR_PLANO:
        return MESES_POR_PLANO[chave]
    return 1  # plano desconhecido: trata como mensal


def avancar_meses(data: date, meses: int) -> date:
    """Avança `meses` a partir de `data`, preservando o dia ou ajustando ao último dia do mês."""
    ano = data.year + (data.month - 1 + meses) // 12
    mes = (data.month - 1 + meses) % 12 + 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    dia = min(data.day, ultimo_dia)
    return date(ano, mes, dia)


def avancar_vencimento(vencimento: date | str | None, plano: str) -> date:
    """Avança o vencimento de planos mensais ou anuais.

    Preserva o dia sempre que possível ou ajusta para o último dia do mês de destino.
    Rejeita planos que não possuem renovação recorrente (ex: vitalício) ou datas inválidas.
    """
    d = para_data(vencimento)
    if d is None:
        raise ValueError("Data de vencimento inválida ou não informada.")
    p = normalizar(plano)
    if p in ("vitalício", "vitalicio"):
        raise ValueError("Plano vitalício não permite pagamento recorrente.")
    meses = {"mensal": 1, "anual": 12}.get(p)
    if meses is None:
        raise ValueError(f"O plano '{plano}' não suporta renovação recorrente.")
    return avancar_meses(d, meses)


def custo_mensal(valor, plano, status=STATUS_ATIVO) -> float:
    """RF-06: só ativas; anual / 12; vitalício não entra."""
    if normalizar(status) != normalizar(STATUS_ATIVO):
        return 0.0
    numero = para_numero(valor)
    meses = meses_do_plano(plano)
    if numero is None or numero <= 0 or meses is None:
        return 0.0
    return numero / meses


def nivel_alerta(dias: int | None) -> str:
    """'vermelho' (vencida ou até 7 dias), 'amarelo' (8 a 30), 'verde' (> 30), 'nenhum'."""
    if dias is None:
        return "nenhum"
    if dias <= 7:
        return "vermelho"
    if dias <= 30:
        return "amarelo"
    return "verde"


EMOJI_ALERTA = {"vermelho": "🔴", "amarelo": "🟡", "verde": "🟢", "nenhum": "⚪"}


def texto_alerta(dias: int | None) -> str:
    if dias is None:
        return "Sem vencimento"
    if dias < 0:
        return f"Vencida há {-dias} dia{'s' if dias != -1 else ''}"
    if dias == 0:
        return "Vence hoje"
    if dias == 1:
        return "Vence amanhã"
    return f"Vence em {dias} dias"


def preparar_assinaturas(df: pd.DataFrame, hoje: date) -> pd.DataFrame:
    """Acrescenta colunas calculadas à aba Assinaturas."""
    df = df.copy()
    if df.empty:
        for col in ("valor_num", "venc_data", "mensal", "dias", "nivel", "alerta", "texto_alerta"):
            df[col] = pd.Series(dtype=object)
        return df
    df["valor_num"] = df["Valor (R$)"].map(para_numero)
    df["venc_data"] = df["Vencimento"].map(para_data)
    # arredondado por item: cards, gráficos e relatórios somam o mesmo número
    df["mensal"] = [round(custo_mensal(v, p, s), 2) for v, p, s in
                    zip(df["Valor (R$)"], df["Plano"], df["Status"])]
    cancelada = df["Status"].map(normalizar) == "cancelada"
    dias = [None if (d is None or canc) else (d - hoje).days
            for d, canc in zip(df["venc_data"], cancelada)]
    df["dias"] = pd.Series(dias, index=df.index, dtype=object)
    df["nivel"] = df["dias"].map(nivel_alerta)
    df["alerta"] = df["nivel"].map(EMOJI_ALERTA)
    df["texto_alerta"] = df["dias"].map(texto_alerta)
    return df


def ativas(df_prep: pd.DataFrame) -> pd.DataFrame:
    if df_prep.empty:
        return df_prep
    return df_prep[df_prep["Status"].map(normalizar) == normalizar(STATUS_ATIVO)]


def indicadores(df_prep: pd.DataFrame, df_func: pd.DataFrame) -> dict:
    """RF-05: os 5 cards do dashboard."""
    at = ativas(df_prep)
    mensal = round(float(at["mensal"].sum()), 2) if not at.empty else 0.0
    if df_prep.empty:
        vencendo = vencidas = 0
    else:
        d = df_prep["dias"].dropna()
        vencendo = int(((d >= 0) & (d <= 30)).sum())
        vencidas = int((d < 0).sum())
    return {
        "total_ativas": int(len(at)),
        "gasto_mensal": mensal,
        "gasto_anual": mensal * 12,
        "vencendo_30": vencendo,
        "vencidas": vencidas,
        "colaboradores": int(len(df_func)),
    }


def gasto_por_categoria(df_prep: pd.DataFrame) -> pd.DataFrame:
    at = ativas(df_prep)
    if at.empty:
        return pd.DataFrame(columns=["Categoria", "Gasto mensal"])
    g = (at.assign(Categoria=at["Categoria"].replace("", "Sem categoria"))
           .groupby("Categoria", as_index=False)["mensal"].sum()
           .rename(columns={"mensal": "Gasto mensal"}))
    g["Gasto mensal"] = g["Gasto mensal"].round(2)
    g = g[g["Gasto mensal"] > 0]
    return g.sort_values("Gasto mensal", ascending=False).reset_index(drop=True)


def contagem_por_status(df_prep: pd.DataFrame, ordem: list[str] | None = None) -> pd.DataFrame:
    if df_prep.empty:
        return pd.DataFrame(columns=["Status", "Quantidade"])
    c = (df_prep.assign(Status=df_prep["Status"].replace("", "Sem status"))
         .groupby("Status", as_index=False).size()
         .rename(columns={"size": "Quantidade"}))
    if ordem:
        pos = {s: i for i, s in enumerate(ordem)}
        c = c.assign(_o=c["Status"].map(lambda s: pos.get(s, 99))).sort_values("_o").drop(columns="_o")
    return c.reset_index(drop=True)


def top_mais_caras(df_prep: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    at = ativas(df_prep)
    if at.empty:
        return pd.DataFrame(columns=["Nome", "Gasto mensal"])
    t = at[at["mensal"] > 0].nlargest(n, "mensal")[["Nome", "mensal", "Plano", "valor_num"]]
    return t.rename(columns={"mensal": "Gasto mensal"}).reset_index(drop=True)


def alertas(df_prep: pd.DataFrame) -> pd.DataFrame:
    """RF-08: lista ordenada por urgência (só assinaturas com vencimento)."""
    if df_prep.empty:
        return df_prep
    a = df_prep[df_prep["dias"].notna()].copy()
    a["_ordem"] = a["dias"].astype(int)
    return a.sort_values("_ordem").drop(columns="_ordem")


def a_vencer(df_prep: pd.DataFrame, dias: int) -> pd.DataFrame:
    if df_prep.empty:
        return df_prep
    a = alertas(df_prep)
    return a[a["dias"].astype(int) <= dias]


# --------------------------------------------------------------------------
# Vínculos e custo por pessoa (RF-20, RF-30)
# --------------------------------------------------------------------------
def usuarios_por_assinatura(df_func: pd.DataFrame) -> dict[str, list[str]]:
    """{nome da assinatura: [IDs dos funcionários]}"""
    mapa: dict[str, list[str]] = {}
    if df_func.empty:
        return mapa
    for _, f in df_func.iterrows():
        for nome in separar_lista(f["Assinaturas"]):
            mapa.setdefault(nome, []).append(str(f["ID"]))
    return mapa


def custo_por_pessoa(df_prep: pd.DataFrame, df_func: pd.DataFrame) -> pd.DataFrame:
    """Custo mensal de cada pessoa: cada assinatura é dividida entre os seus usuários."""
    cols = ["ID", "Nome completo", "E-mail", "Departamento", "Cargo", "Qtd. assinaturas", "Custo mensal"]
    if df_func.empty:
        return pd.DataFrame(columns=cols)
    usuarios = usuarios_por_assinatura(df_func)
    custo_assin = {}
    if not df_prep.empty:
        custo_assin = dict(zip(df_prep["Nome"].astype(str), df_prep["mensal"]))
    linhas = []
    for _, f in df_func.iterrows():
        nomes = separar_lista(f["Assinaturas"])
        total = 0.0
        for n in nomes:
            qtd = len(usuarios.get(n, [])) or 1
            total += float(custo_assin.get(n, 0.0)) / qtd
        linhas.append({
            "ID": f["ID"], "Nome completo": f["Nome completo"], "E-mail": f["E-mail"],
            "Departamento": f["Departamento"] or "Sem departamento", "Cargo": f["Cargo"],
            "Qtd. assinaturas": len(nomes), "Custo mensal": round(total, 2),
        })
    return pd.DataFrame(linhas, columns=cols)


def detalhe_pessoa(df_prep: pd.DataFrame, df_func: pd.DataFrame, id_pessoa: str) -> pd.DataFrame:
    """Assinaturas de uma pessoa, com a parte do custo que cabe a ela."""
    pessoa = df_func[df_func["ID"].astype(str) == str(id_pessoa)]
    if pessoa.empty:
        return pd.DataFrame()
    usuarios = usuarios_por_assinatura(df_func)
    linhas = []
    for nome in separar_lista(pessoa.iloc[0]["Assinaturas"]):
        reg = df_prep[df_prep["Nome"].astype(str) == nome] if not df_prep.empty else df_prep
        if reg.empty:
            linhas.append({"Assinatura": nome, "Plano": "—", "Status": "Não encontrada",
                           "Usuários": len(usuarios.get(nome, [])), "Custo mensal total": 0.0,
                           "Parte da pessoa": 0.0})
            continue
        r = reg.iloc[0]
        qtd = len(usuarios.get(nome, [])) or 1
        linhas.append({"Assinatura": nome, "Plano": r["Plano"], "Status": r["Status"],
                       "Usuários": qtd, "Custo mensal total": float(r["mensal"]),
                       "Parte da pessoa": round(float(r["mensal"]) / qtd, 2)})
    return pd.DataFrame(linhas)


def gasto_por_departamento(df_prep: pd.DataFrame, df_func: pd.DataFrame) -> pd.DataFrame:
    cp = custo_por_pessoa(df_prep, df_func)
    if cp.empty:
        return pd.DataFrame(columns=["Departamento", "Colaboradores", "Gasto mensal", "Gasto anual"])
    g = cp.groupby("Departamento", as_index=False).agg(
        Colaboradores=("ID", "count"), **{"Gasto mensal": ("Custo mensal", "sum")})
    g["Gasto mensal"] = g["Gasto mensal"].round(2)
    g["Gasto anual"] = (g["Gasto mensal"] * 12).round(2)
    return g.sort_values("Gasto mensal", ascending=False).reset_index(drop=True)


def colaboradores_por_assinatura(df_prep: pd.DataFrame, df_func: pd.DataFrame) -> pd.DataFrame:
    usuarios = usuarios_por_assinatura(df_func)
    nomes_func = dict(zip(df_func["ID"].astype(str), df_func["Nome completo"])) if not df_func.empty else {}
    linhas = []
    if not df_prep.empty:
        for _, a in df_prep.sort_values("Nome").iterrows():
            ids = usuarios.get(str(a["Nome"]), [])
            linhas.append({
                "Assinatura": a["Nome"], "Categoria": a["Categoria"], "Status": a["Status"],
                "Qtd. usuários": len(ids),
                "Usuários": ", ".join(sorted(nomes_func.get(i, i) for i in ids)),
                "Gasto mensal": float(a["mensal"]),
                "Custo por usuário": round(float(a["mensal"]) / len(ids) if ids else float(a["mensal"]), 2),
            })
    return pd.DataFrame(linhas, columns=["Assinatura", "Categoria", "Status", "Qtd. usuários",
                                         "Usuários", "Gasto mensal", "Custo por usuário"])


def projetos_por_assinatura(projetos: pd.DataFrame, usos: pd.DataFrame) -> dict[str, list[str]]:
    """Retorna {ID da assinatura: [nomes dos projetos ativos]} a partir dos vínculos."""
    if projetos.empty or usos.empty:
        return {}
    nomes = dict(zip(projetos["ID"].astype(str), projetos["Nome"].astype(str)))
    ativos = usos[usos["Status"].map(normalizar).isin(("ativo", "ativa"))]
    mapa: dict[str, list[str]] = {}
    for _, uso in ativos.iterrows():
        nome = nomes.get(str(uso["Projeto ID"]))
        if nome:
            mapa.setdefault(str(uso["Assinatura ID"]), []).append(nome)
    return {k: sorted(set(v)) for k, v in mapa.items()}


def custos_por_projeto(assinaturas: pd.DataFrame, projetos: pd.DataFrame, usos: pd.DataFrame) -> pd.DataFrame:
    """Divide igualmente o custo de cada assinatura entre seus projetos ativos."""
    colunas = ["ID", "Projeto", "Cliente", "Status", "Assinaturas", "Custo mensal", "Custo anual"]
    if projetos.empty:
        return pd.DataFrame(columns=colunas)
    custos = dict(zip(assinaturas["ID"].astype(str), assinaturas["mensal"])) if not assinaturas.empty else {}
    ativos = usos[usos["Status"].map(normalizar).isin(("ativo", "ativa"))] if not usos.empty else usos
    qtd_por_ass = ativos.groupby(ativos["Assinatura ID"].astype(str)).size().to_dict() if not ativos.empty else {}
    linhas = []
    for _, projeto in projetos.iterrows():
        vinculos = ativos[ativos["Projeto ID"].astype(str) == str(projeto["ID"])] if not ativos.empty else ativos
        ids = vinculos["Assinatura ID"].astype(str).unique().tolist() if not vinculos.empty else []
        mensal = sum(float(custos.get(i, 0)) / max(1, qtd_por_ass.get(i, 1)) for i in ids)
        linhas.append({
            "ID": projeto["ID"], "Projeto": projeto["Nome"], "Cliente": projeto["Cliente"],
            "Status": projeto["Status"], "Assinaturas": len(ids),
            "Custo mensal": round(mensal, 2), "Custo anual": round(mensal * 12, 2),
        })
    return pd.DataFrame(linhas, columns=colunas)


# --------------------------------------------------------------------------
# Evolução do gasto em 12 meses (RF-07), reconstruída pelo Histórico
# --------------------------------------------------------------------------
_CAMPO_COLUNA = {"Valor (R$)": "Valor (R$)", "Valor": "Valor (R$)", "Plano": "Plano",
                 "Status": "Status", "Nome": "Nome"}


def _fim_do_mes(ano, mes) -> datetime:
    if mes == 12:
        return datetime(ano + 1, 1, 1) - timedelta(seconds=1)
    return datetime(ano, mes + 1, 1) - timedelta(seconds=1)


def evolucao_12_meses(df_ass: pd.DataFrame, df_hist: pd.DataFrame, agora: datetime) -> pd.DataFrame:
    """Gasto mensal ao fim de cada um dos últimos 12 meses.

    Parte do estado atual e "desfaz" as alterações do Histórico posteriores
    a cada mês (valor, plano, status e nome). Assinaturas cadastradas depois
    do mês não entram. Assinaturas já excluídas não aparecem.
    """
    meses = []
    ano, mes = agora.year, agora.month
    for _ in range(12):
        meses.append((ano, mes))
        mes -= 1
        if mes == 0:
            ano, mes = ano - 1, 12
    meses.reverse()

    base = df_ass.copy()
    if not base.empty:
        base["_cad"] = pd.to_datetime(base["Cadastrado em"].map(para_datahora), errors="coerce")
    eventos = []
    if df_hist is not None and not df_hist.empty:
        for _, h in df_hist.iterrows():
            col = _CAMPO_COLUNA.get(str(h.get("Campo", "")).strip())
            quando = para_datahora(h.get("Data e hora"))
            if col and quando and str(h.get("Valor anterior", "")).strip() != "(não disponível)":
                eventos.append((quando, str(h.get("Assinatura", "")), col,
                                h.get("Valor anterior", ""), str(h.get("Evento", ""))))
        eventos.sort(key=lambda e: e[0], reverse=True)

    resultado = []
    for ano, mes in meses:
        fim = min(_fim_do_mes(ano, mes), agora)
        total = 0.0
        if not base.empty:
            estado = base[(base["_cad"].isna()) | (base["_cad"] <= fim)].astype(object)
            for quando, nome, col, anterior, evento in eventos:
                if quando <= fim:
                    break
                alvo = estado.index[estado["Nome"].astype(str) == nome]
                if len(alvo) == 0:
                    continue
                if col == "Nome" or evento == EV_RENOMEADA:
                    estado.loc[alvo, "Nome"] = str(anterior)
                else:
                    estado.loc[alvo, col] = anterior
            total = sum(custo_mensal(v, p, s) for v, p, s in
                        zip(estado["Valor (R$)"], estado["Plano"], estado["Status"]))
        resultado.append({"Mês": f"{mes:02d}/{ano}", "Gasto mensal": round(total, 2)})
    return pd.DataFrame(resultado)
