from __future__ import annotations

from dataclasses import dataclass

from app.analysis.volatility import VolatilitySnapshot


@dataclass(slots=True)
class PositionSizing:
    quantity: float
    leverage: int
    notional: float
    cost: float
    stop_loss: float
    take_profit: float
    trailing_active: bool


class RiskManager:
    def __init__(
        self,
        quote_balance: float,
        leverage: int,
        risk_perc: float,
        config: dict[str, float],
        fixed_cost: float = 0.0,
    ) -> None:
        self._balance = quote_balance
        self._leverage = leverage
        self._risk_perc = risk_perc / 100 if risk_perc > 1 else risk_perc
        self._config = config
        self._fixed_cost = max(fixed_cost, 0.0)

    @property
    def leverage(self) -> int:
        return self._leverage

    @property
    def fixed_cost(self) -> float:
        return self._fixed_cost

    def _position_risk(self) -> float:
        return self._balance * self._risk_perc

    def _empty_sizing(self) -> PositionSizing:
        return PositionSizing(
            quantity=0.0,
            leverage=self._leverage,
            notional=0.0,
            cost=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            trailing_active=False,
        )

    def size_position(self, price: float, volatility: VolatilitySnapshot, direction: str) -> PositionSizing:
        if direction not in {"long", "short"}:
            return self._empty_sizing()

        atr = volatility.atr
        atr_multiplier_sl = self._config.get("atr_multiplier_sl", 2.5)
        atr_multiplier_tp = self._config.get("atr_multiplier_tp", 4.0)
        trailing = self._config.get("trailing_stop", True)
        trailing_mult = self._config.get("trailing_atr_multiplier", 1.5)

        if price <= 0:
            return self._empty_sizing()

        stop_distance = atr * atr_multiplier_sl
        if stop_distance <= 0:
            return self._empty_sizing()

        if self._fixed_cost > 0:
            cost = self._fixed_cost
            notional = cost * self._leverage
            quantity = notional / price if price else 0.0
        else:
            risk_amount = self._position_risk()
            quantity = (risk_amount * self._leverage) / stop_distance
            notional = quantity * price
            cost = notional / self._leverage if self._leverage else 0.0

        quantity = max(quantity, 0.0)
        notional = max(notional, 0.0)
        cost = max(cost, 0.0)

        if quantity == 0.0 or notional == 0.0:
            return self._empty_sizing()

        if direction == "long":
            stop_loss = price - stop_distance
            take_profit = price + atr * atr_multiplier_tp
        else:
            stop_loss = price + stop_distance
            take_profit = price - atr * atr_multiplier_tp

        return PositionSizing(
            quantity=quantity,
            leverage=self._leverage,
            notional=notional,
            cost=cost,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_active=bool(trailing) and trailing_mult > 0,
        )


__all__ = ["RiskManager", "PositionSizing"]
