"""Camada de apresentacao (Streamlit e exportacao)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from .metrics import calculate_snapshot, group_by_cost_center, rolling_cashflow


def render_dashboard(frames: dict, last_sync: Optional[str], issues: Iterable[str]) -> None:
    receitas = frames.get("receitas", pd.DataFrame())
    despesas = frames.get("despesas", pd.DataFrame())
    previsoes = frames.get("previsoes", pd.DataFrame())

    snapshot = calculate_snapshot(receitas, despesas, previsoes)
    cashflow = rolling_cashflow(receitas, despesas)
    por_centro = group_by_cost_center(receitas, despesas)

    st.title("Dashboard Financeiro")
    if last_sync:
        st.caption(f"Ultima sincronizacao: {last_sync}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Receitas", f"R$ {snapshot['total_receitas']:,.2f}")
    col2.metric("Despesas", f"R$ {snapshot['total_despesas']:,.2f}")
    col3.metric("Margem", f"R$ {snapshot['margem']:,.2f}")
    col4.metric("Previsto (30d)", f"R$ {snapshot['previsto']:,.2f}")

    st.subheader("Fluxo de caixa acumulado")
    fig_cash = px.line(
        cashflow,
        x="data",
        y="saldo_acumulado",
        markers=True,
        labels={"data": "Data", "saldo_acumulado": "Saldo acumulado"},
    )
    fig_cash.update_layout(yaxis_tickprefix="R$ ")
    st.plotly_chart(fig_cash, use_container_width=True)

    st.subheader("Entradas x saidas por dia")
    fig_bar = px.bar(
        cashflow,
        x="data",
        y=["entradas", "saidas"],
        barmode="group",
        labels={"value": "Valor", "variable": "Categoria"},
    )
    fig_bar.update_layout(yaxis_tickprefix="R$ ")
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Saldo por centro de custo")
    if not por_centro.empty:
        melted = por_centro.melt(id_vars="centro_custo", value_vars=["receitas", "despesas"])
        fig_center = px.bar(
            melted,
            x="centro_custo",
            y="value",
            color="variable",
            barmode="group",
            labels={"value": "Valor", "centro_custo": "Centro de custo"},
        )
        fig_center.update_layout(yaxis_tickprefix="R$ ")
        st.plotly_chart(fig_center, use_container_width=True)
    else:
        st.info("Sem dados de centro de custo para exibir.")

    if not previsoes.empty:
        st.subheader("Eventos previstos")
        st.dataframe(previsoes.sort_values("data"), use_container_width=True)

    if issues:
        st.warning("Logs da ultima sincronizacao:")
        for issue in issues:
            st.write(f"- {issue}")


def export_report(frames: dict, output: Path, issues: Iterable[str]) -> Path:
    """Gera um snapshot HTML que pode ser convertido em PDF."""

    receitas = frames.get("receitas", pd.DataFrame())
    despesas = frames.get("despesas", pd.DataFrame())
    previsoes = frames.get("previsoes", pd.DataFrame())
    snapshot = calculate_snapshot(receitas, despesas, previsoes)
    cashflow = rolling_cashflow(receitas, despesas)
    centros = group_by_cost_center(receitas, despesas)

    html = [
        "<html><head><meta charset='utf-8'><title>Dashboard Financeiro</title>",
        "<style>body{font-family:Arial;margin:24px;color:#1f2933;} table{border-collapse:collapse;width:100%;margin-bottom:16px;} th,td{border:1px solid #e2e8f0;padding:8px;text-align:left;} th{background:#f1f5f9;}</style>",
        "</head><body>",
        "<h1>Resumo Financeiro</h1>",
        "<h2>Principais indicadores</h2>",
        "<ul>",
        f"<li>Receitas: R$ {snapshot['total_receitas']:,.2f}</li>",
        f"<li>Despesas: R$ {snapshot['total_despesas']:,.2f}</li>",
        f"<li>Margem: R$ {snapshot['margem']:,.2f}</li>",
        f"<li>Previsto (30d): R$ {snapshot['previsto']:,.2f}</li>",
        "</ul>",
        "<h2>Fluxo de caixa diario</h2>",
        cashflow.to_html(index=False),
        "<h2>Saldo por centro de custo</h2>",
        centros.to_html(index=False),
    ]
    if not previsoes.empty:
        html.append("<h2>Eventos previstos</h2>")
        html.append(previsoes.sort_values("data").to_html(index=False))
    if issues:
        html.append("<h2>Logs</h2><ul>")
        for item in issues:
            html.append(f"<li>{item}</li>")
        html.append("</ul>")
    html.append("</body></html>")

    output.write_text("".join(html), encoding="utf-8")
    return output
