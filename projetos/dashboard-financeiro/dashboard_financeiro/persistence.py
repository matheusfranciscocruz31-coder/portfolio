"""Persistencia basica em SQLite para o dashboard financeiro."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd


class FinanceRepository:
    """Encapsula operacoes de leitura/escrita no SQLite."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            conn.commit()

    def write_table(self, name: str, frame: pd.DataFrame) -> None:
        with self.connection() as conn:
            frame.to_sql(name, conn, if_exists="replace", index=False)
            conn.commit()

    def read_table(self, name: str) -> pd.DataFrame:
        with self.connection() as conn:
            try:
                return pd.read_sql_query(f"SELECT * FROM {name}", conn, parse_dates=["data"])
            except Exception:
                return pd.DataFrame()

    def register_sync(self, when: datetime) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES(?, ?)",
                ("last_sync", when.isoformat()),
            )
            conn.commit()

    def last_sync(self) -> datetime | None:
        with self.connection() as conn:
            cur = conn.execute("SELECT value FROM metadata WHERE key = ?", ("last_sync",))
            row = cur.fetchone()
            if row:
                return datetime.fromisoformat(row[0])
            return None

    def load_all(self) -> Dict[str, pd.DataFrame]:
        return {
            "receitas": self.read_table("receitas"),
            "despesas": self.read_table("despesas"),
            "previsoes": self.read_table("previsoes"),
        }
