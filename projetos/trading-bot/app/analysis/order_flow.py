from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque


@dataclass(slots=True)
class OrderFlowSnapshot:
    buy_volume: float
    sell_volume: float
    delta: float
    imbalance: float
    liquidation_pressure: float


class OrderFlowAnalyzer:
    """Tracks order flow, aggression and liquidation pressure in rolling windows."""

    def __init__(self, maxlen: int = 120):
        self._trades: Deque[tuple[float, float, bool]] = deque(maxlen=maxlen)
        self._liquidations: Deque[tuple[float, bool]] = deque(maxlen=maxlen)

    def update_from_trade(self, price: float, quantity: float, is_buyer_maker: bool) -> OrderFlowSnapshot:
        is_buy_aggressor = not is_buyer_maker
        self._trades.append((price, quantity, is_buy_aggressor))
        return self.snapshot()

    def update_from_liquidation(self, quantity: float, side: str) -> OrderFlowSnapshot:
        is_long_liq = side.upper() == "BUY"
        self._liquidations.append((quantity, is_long_liq))
        return self.snapshot()

    def snapshot(self) -> OrderFlowSnapshot:
        buy_volume = sum(q for _, q, is_buy in self._trades if is_buy)
        sell_volume = sum(q for _, q, is_buy in self._trades if not is_buy)
        delta = buy_volume - sell_volume
        total = buy_volume + sell_volume
        imbalance = (delta / total) if total else 0.0

        long_liq = sum(q for q, is_long in self._liquidations if is_long)
        short_liq = sum(q for q, is_long in self._liquidations if not is_long)
        liquidation_total = long_liq + short_liq
        liquidation_pressure = (short_liq - long_liq) / liquidation_total if liquidation_total else 0.0

        return OrderFlowSnapshot(
            buy_volume=buy_volume,
            sell_volume=sell_volume,
            delta=delta,
            imbalance=imbalance,
            liquidation_pressure=liquidation_pressure,
        )


__all__ = ["OrderFlowAnalyzer", "OrderFlowSnapshot"]
