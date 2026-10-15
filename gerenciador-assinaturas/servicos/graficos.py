"""Os 4 gráficos do dashboard (RF-07), em Plotly.

As mesmas figuras viram imagem nos relatórios em PDF (via Kaleido).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

PALETA = ["#3b82f6", "#8b5cf6", "#06b6d4", "#f59e0b", "#10b981", "#ec4899", "#64748b", "#ef4444"]
COR_STATUS = {"Ativa": "#10b981", "Em teste": "#3b82f6", "Pausada": "#f59e0b", "Cancelada": "#94a3b8"}


def _reais(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _layout(fig: go.Figure, altura=320, legenda=False):
    fig.update_layout(
        height=altura, margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=13),
        showlegend=legenda, separators=",.",
        hoverlabel=dict(font_family="Inter, sans-serif"),
    )
    return fig


def vazio(msg="Sem dados para mostrar") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=14, color="#94a3b8"))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _layout(fig)


def donut_categoria(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return vazio("Nenhuma assinatura ativa com valor")
    fig = go.Figure(go.Pie(
        labels=df["Categoria"], values=df["Gasto mensal"], hole=0.58, sort=True,
        marker=dict(colors=PALETA, line=dict(width=0)),
        texttemplate="%{percent:.0%}", textposition="inside",
        customdata=[_reais(v) for v in df["Gasto mensal"]],
        hovertemplate="<b>%{label}</b><br>%{customdata} por mês<br>%{percent:.1%}<extra></extra>",
    ))
    total = df["Gasto mensal"].sum()
    fig.add_annotation(text=f"<b>{_reais(total)}</b><br><span style='font-size:11px'>por mês</span>",
                       showarrow=False, font=dict(size=15))
    fig = _layout(fig, legenda=True)
    fig.update_layout(legend=dict(orientation="v", x=1.0, y=0.5, font=dict(size=12)))
    return fig


def barras_status(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return vazio()
    df = df.iloc[::-1]
    fig = go.Figure(go.Bar(
        x=df["Quantidade"], y=df["Status"], orientation="h",
        marker=dict(color=[COR_STATUS.get(s, "#64748b") for s in df["Status"]], cornerradius=6),
        text=df["Quantidade"], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b>: %{x} assinatura(s)<extra></extra>",
    ))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(showgrid=False)
    return _layout(fig)


def linha_evolucao(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return vazio()
    fig = go.Figure(go.Scatter(
        x=df["Mês"], y=df["Gasto mensal"], mode="lines+markers",
        line=dict(color="#6366f1", width=3, shape="spline", smoothing=0.6),
        marker=dict(size=7, color="#6366f1"),
        fill="tozeroy", fillcolor="rgba(99,102,241,0.12)",
        customdata=[_reais(v) for v in df["Gasto mensal"]],
        hovertemplate="<b>%{x}</b><br>%{customdata}<extra></extra>",
    ))
    fig.update_yaxes(tickprefix="R$ ", tickformat=",.0f", gridcolor="rgba(148,163,184,0.25)", rangemode="tozero")
    fig.update_xaxes(showgrid=False)
    return _layout(fig)


def barras_top5(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return vazio("Nenhuma assinatura ativa com valor")
    df = df.iloc[::-1]
    fig = go.Figure(go.Bar(
        x=df["Gasto mensal"], y=df["Nome"], orientation="h",
        marker=dict(color="#3b82f6", cornerradius=6),
        text=[_reais(v) for v in df["Gasto mensal"]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{text} por mês<extra></extra>",
    ))
    fig.update_xaxes(visible=False, range=[0, df["Gasto mensal"].max() * 1.35])
    fig.update_yaxes(showgrid=False)
    return _layout(fig)
