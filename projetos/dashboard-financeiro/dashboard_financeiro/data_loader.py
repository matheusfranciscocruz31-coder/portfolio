"""Sincronizacao de fontes (CSV, Sheets) para o dashboard financeiro."""

from __future__ import annotations

import argparse
import datetime as dt
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
import tomli

from .persistence import FinanceRepository

LOGGER = logging.getLogger("dashboard_financeiro")

DEFAULT_CONFIG_PATH = Path("settings.toml")

REQUIRED_RECEITAS = {"data", "cliente", "centro_custo", "descricao", "valor"}
REQUIRED_DESPESAS = {"data", "fornecedor", "centro_custo", "descricao", "valor"}
REQUIRED_PREVISOES = {"data", "centro_custo", "descricao", "valor_previsto"}


def load_config(path: Optional[Path]) -> Dict:
    if path and path.exists():
        return tomli.loads(path.read_text(encoding="utf-8"))
    base_dir = Path(__file__).resolve().parents[1]
    return {
        "paths": {
            "receitas": str(base_dir / "data" / "receitas.csv"),
            "despesas": str(base_dir / "data" / "despesas.csv"),
            "previsoes": str(base_dir / "data" / "previsoes.csv"),
            "database": str(base_dir / "finance.db"),
        },
        "google_sheets": {"enabled": False},
    }


def _read_csv(path: Path, required: Iterable[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")
    frame = pd.read_csv(path)
    missing = set(required) - {c.lower() for c in frame.columns.str.lower()}
    if missing:
        raise ValueError(f"Colunas ausentes em {path.name}: {', '.join(sorted(missing))}")
    frame.columns = [c.lower() for c in frame.columns]
    return frame[list(required)]


def _normalise_dates(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date
    return df.dropna(subset=["data"])


def _apply_numeric(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    df = frame.copy()
    df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)
    return df


def _load_sources(config: Dict, base_dir: Path) -> Dict[str, pd.DataFrame]:
    issues: List[str] = []
    def resolve(path_str: str) -> Path:
        path = Path(path_str)
        if not path.is_absolute():
            path = base_dir / path
        return path

    frames: Dict[str, pd.DataFrame] = {}
    try:
        receitas = _read_csv(resolve(config["paths"]["receitas"]), REQUIRED_RECEITAS)
        frames["receitas"] = _apply_numeric(_normalise_dates(receitas), "valor")
    except Exception as exc:
        issues.append(str(exc))
        frames["receitas"] = pd.DataFrame(columns=list(REQUIRED_RECEITAS))

    try:
        despesas = _read_csv(resolve(config["paths"]["despesas"]), REQUIRED_DESPESAS)
        despesas = _apply_numeric(_normalise_dates(despesas), "valor")
        if (despesas["valor"] > 0).any():
            despesas.loc[:, "valor"] = despesas["valor"] * -1
        frames["despesas"] = despesas
    except Exception as exc:
        issues.append(str(exc))
        frames["despesas"] = pd.DataFrame(columns=list(REQUIRED_DESPESAS))

    try:
        previsoes = _read_csv(resolve(config["paths"]["previsoes"]), REQUIRED_PREVISOES)
        frames["previsoes"] = _apply_numeric(_normalise_dates(previsoes), "valor_previsto")
    except Exception as exc:
        issues.append(str(exc))
        frames["previsoes"] = pd.DataFrame(columns=list(REQUIRED_PREVISOES))

    frames["issues"] = issues
    return frames


def sync_sources(config_path: Optional[Path] = None) -> Dict:
    """Executa a sincronizacao e persiste dados no SQLite."""

    config = load_config(config_path)
    base_dir = config_path.parent if config_path else Path(__file__).resolve().parents[1]
    frames = _load_sources(config, base_dir.resolve())
    issues = frames.pop("issues", [])

    db_path = Path(config["paths"]["database"])
    if not db_path.is_absolute():
        db_path = base_dir.resolve() / db_path

    repo = FinanceRepository(db_path)
    repo.write_table("receitas", frames["receitas"])
    repo.write_table("despesas", frames["despesas"])
    repo.write_table("previsoes", frames["previsoes"])
    repo.register_sync(dt.datetime.utcnow())

    LOGGER.info("Sincronizacao concluida. Base salva em %s", repo.db_path)

    return {
        "frames": frames,
        "issues": issues,
        "repository": repo,
        "config": config,
    }


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sincroniza dados para o dashboard financeiro.")
    subparsers = parser.add_subparsers(dest="command")

    sync_parser = subparsers.add_parser("sync", help="Carrega fontes e atualiza o banco de dados.")
    sync_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    sync_parser.add_argument("--verbose", action="store_true")

    ns = parser.parse_args(argv)
    if ns.command is None:
        parser.error("Informe um comando (ex.: sync)")
    return ns


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    _configure_logging(args.verbose)
    try:
        result = sync_sources(args.config)
    except Exception as exc:
        LOGGER.error("Falha durante a sincronizacao: %s", exc)
        return 1

    for issue in result["issues"]:
        LOGGER.warning(issue)

    LOGGER.info("Receitas sincronizadas: %s linhas", len(result["frames"]["receitas"]))
    LOGGER.info("Despesas sincronizadas: %s linhas", len(result["frames"]["despesas"]))
    LOGGER.info("Previsoes sincronizadas: %s linhas", len(result["frames"]["previsoes"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
