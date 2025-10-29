"""Entrypoint do dashboard financeiro (Streamlit / export)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from dashboard_financeiro.data_loader import sync_sources
from dashboard_financeiro.ui import export_report, render_dashboard


def parse_cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config", type=Path, help="Arquivo de configuracao TOML.")
    parser.add_argument(
        "--export",
        choices=["html"],
        help="Gera snapshot offline do dashboard (HTML).",
    )
    parser.add_argument("--output", type=Path, help="Caminho do arquivo exportado.")
    args, _ = parser.parse_known_args()
    return args


def _resolve_config(path: Optional[Path]) -> Optional[Path]:
    if path and path.exists():
        return path
    default = Path("settings.toml")
    return default if default.exists() else None


def run_export(config_path: Optional[Path], output: Optional[Path]) -> None:
    result = sync_sources(config_path)
    frames = result["frames"]
    issues = result["issues"]
    target = output or Path("dashboard_snapshot.html")
    export_report(frames, target, issues)
    print(f"[OK] Snapshot gerado em {target.resolve()}")


def run_streamlit(config_path: Optional[Path]) -> None:
    import streamlit as st

    st.set_page_config(page_title="Dashboard Financeiro", layout="wide")
    result = sync_sources(config_path)
    frames = result["frames"]
    repo = result["repository"]
    issues = result["issues"]

    last_sync = repo.last_sync()
    render_dashboard(frames, last_sync.isoformat() if last_sync else None, issues)


def main() -> None:
    args = parse_cli()
    config_path = _resolve_config(args.config)
    if args.export:
        run_export(config_path, args.output)
    else:
        run_streamlit(config_path)


if __name__ == "__main__":
    main()
