"""Metricas auxiliares para o dashboard financeiro."""

from __future__ import annotations

import pandas as pd


def _ensure_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame()
    return frame.copy()


def calculate_snapshot(receitas: pd.DataFrame, despesas: pd.DataFrame, previsoes: pd.DataFrame | None = None) -> dict:
    rec = _ensure_frame(receitas)
    dep = _ensure_frame(despesas)
    prev = _ensure_frame(previsoes)

    total_receitas = float(rec.get("valor", pd.Series(dtype=float)).sum())
    total_despesas = float(dep.get("valor", pd.Series(dtype=float)).sum())
    margem = total_receitas + total_despesas  # despesas ja negativas
    ticket_medio = float(
        total_receitas / max(len(rec), 1)
    )
    projecao = float(prev.get("valor_previsto", pd.Series(dtype=float)).sum()) if not prev.empty else 0.0

    return {
        "total_receitas": total_receitas,
        "total_despesas": total_despesas,
        "margem": margem,
        "ticket_medio": ticket_medio,
        "previsto": projecao,
    }


def rolling_cashflow(receitas: pd.DataFrame, despesas: pd.DataFrame) -> pd.DataFrame:
    rec = _ensure_frame(receitas)
    dep = _ensure_frame(despesas)

    rec = rec.assign(valor=rec.get("valor", 0.0)).groupby("data", as_index=False)["valor"].sum()
    dep = dep.assign(valor=dep.get("valor", 0.0)).groupby("data", as_index=False)["valor"].sum()

    cash = pd.merge(rec, dep, on="data", how="outer", suffixes=("_receitas", "_despesas")).fillna(0.0)
    cash["entradas"] = cash["valor_receitas"]
    cash["saidas"] = cash["valor_despesas"]
    cash["saldo_dia"] = cash["entradas"] + cash["saidas"]  # saidas negativas
    cash = cash.sort_values("data")
    cash["saldo_acumulado"] = cash["saldo_dia"].cumsum()
    return cash[["data", "entradas", "saidas", "saldo_dia", "saldo_acumulado"]]


def group_by_cost_center(receitas: pd.DataFrame, despesas: pd.DataFrame) -> pd.DataFrame:
    rec = _ensure_frame(receitas)
    dep = _ensure_frame(despesas)

    rec_summary = (
        rec.groupby("centro_custo", as_index=False)["valor"]
        .sum()
        .rename(columns={"valor": "receitas"})
    )
    dep_summary = (
        dep.groupby("centro_custo", as_index=False)["valor"]
        .sum()
        .rename(columns={"valor": "despesas"})
    )
    summary = pd.merge(rec_summary, dep_summary, on="centro_custo", how="outer").fillna(0.0)
    summary["saldo"] = summary["receitas"] + summary["despesas"]
    summary = summary.sort_values("saldo", ascending=False)
    return summary
