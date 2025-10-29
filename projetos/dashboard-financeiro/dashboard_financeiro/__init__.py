"""Pacote do dashboard financeiro."""

from .data_loader import sync_sources
from .metrics import calculate_snapshot, group_by_cost_center, rolling_cashflow
from .persistence import FinanceRepository

__all__ = [
    "sync_sources",
    "calculate_snapshot",
    "group_by_cost_center",
    "rolling_cashflow",
    "FinanceRepository",
]
