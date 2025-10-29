"""Funcoes de limpeza e validacao do dataset de vendas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Tuple

import pandas as pd

CANONICAL_COLUMNS = ["data", "cliente", "produto", "quantidade", "valor"]

COLUMN_ALIASES: Dict[str, Iterable[str]] = {
    "data": {"data", "dt", "dt_venda", "data_venda"},
    "cliente": {"cliente", "cliente_nome", "comprador"},
    "produto": {"produto", "item", "sku", "descricao"},
    "quantidade": {"quantidade", "qtd", "quant", "qtdade"},
    "valor": {"valor", "preco", "receita", "total"},
}


@dataclass
class ValidationResult:
    """Saida padronizada da validacao."""

    frame: pd.DataFrame
    issues: List[str]


def _canonical_name(raw: str) -> str | None:
    for canonical, aliases in COLUMN_ALIASES.items():
        if raw.lower() in aliases:
            return canonical
    return None


def normalise_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Mapeia colunas para os nomes canonicos esperados."""

    rename_map: Dict[str, str] = {}
    for col in frame.columns:
        canonical = _canonical_name(col)
        if canonical:
            if canonical in rename_map.values():
                continue
            rename_map[col] = canonical
    return frame.rename(columns=rename_map)


def ensure_required_columns(frame: pd.DataFrame) -> List[str]:
    """Verifica presenca das colunas obrigatorias."""

    missing = [c for c in CANONICAL_COLUMNS if c not in frame.columns]
    issues = []
    if missing:
        issues.append(
            "Colunas obrigatorias ausentes: "
            + ", ".join(sorted(missing))
        )
    return issues


def coerce_types(frame: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Converte tipos e registra avisos."""

    issues: List[str] = []
    df = frame.copy()

    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date
        n_invalid = df["data"].isna().sum()
        if n_invalid:
            issues.append(f"{n_invalid} linhas com data invalida foram descartadas.")
        df = df.dropna(subset=["data"])

    if "quantidade" in df.columns:
        df["quantidade"] = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0).astype(int)
        invalid = (df["quantidade"] < 0).sum()
        if invalid:
            issues.append(f"{invalid} linhas com quantidade negativa foram ajustadas para zero.")
            df.loc[df["quantidade"] < 0, "quantidade"] = 0

    if "valor" in df.columns:
        df["valor"] = (
            pd.to_numeric(df["valor"], errors="coerce")
            .fillna(0.0)
            .astype(float)
        )
        invalid = (df["valor"] < 0).sum()
        if invalid:
            issues.append(f"{invalid} linhas com valor negativo foram ajustadas para zero.")
            df.loc[df["valor"] < 0, "valor"] = 0.0

    for col in ("cliente", "produto"):
        if col in df.columns:
            df[col] = df[col].fillna("NA").astype(str).str.strip()

    return df, issues


def filter_by_window(frame: pd.DataFrame, janela: str) -> Tuple[pd.DataFrame, str]:
    """Aplica filtros de data baseado na janela desejada."""

    if "data" not in frame.columns or frame["data"].empty:
        return frame, "Sem filtro de data aplicado."

    end = frame["data"].max()
    if not isinstance(end, date):
        return frame, "Datas nao detectadas; filtro ignorado."

    janela = (janela or "").lower()
    if janela not in {"diaria", "semanal", "mensal"}:
        return frame, "Janela padrao (completa) utilizada."

    delta_map = {
        "diaria": timedelta(days=1),
        "semanal": timedelta(weeks=1),
        "mensal": timedelta(days=31),
    }
    start = end - delta_map[janela]
    mask = frame["data"] >= start
    return frame.loc[mask].copy(), f"Filtro {janela} aplicado: {start} a {end}."


def validate_dataset(frame: pd.DataFrame, janela: str = "") -> ValidationResult:
    """Pipeline completo de validacao e normalizacao."""

    issues: List[str] = []

    normalized = normalise_columns(frame)
    issues.extend(ensure_required_columns(normalized))

    cleaned, coercion_issues = coerce_types(normalized)
    issues.extend(coercion_issues)

    filtered, janela_info = filter_by_window(cleaned, janela)
    issues.append(janela_info)

    return ValidationResult(frame=filtered.reset_index(drop=True), issues=issues)
