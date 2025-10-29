from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from loguru import logger


@dataclass(slots=True)
class Position:
    symbol: str
    direction: str
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    trailing_active: bool = False
    notional: float = 0.0
    cost: float = 0.0


@dataclass
class PortfolioState:
    positions: Dict[str, Position] = field(default_factory=dict)


class PortfolioManager:
    def __init__(self, max_positions: int = 1) -> None:
        self._state = PortfolioState()
        self._max_positions = max_positions

    def can_open(self, symbol: str) -> bool:
        if symbol in self._state.positions:
            logger.debug("Position already open", symbol=symbol)
            return False
        return len(self._state.positions) < self._max_positions

    def add_position(self, position: Position) -> None:
        self._state.positions[position.symbol] = position
        logger.info(
            "Position registered",
            symbol=position.symbol,
            direction=position.direction,
            quantity=position.quantity,
            notional=position.notional,
            cost=position.cost,
        )

    def get_position(self, symbol: str) -> Optional[Position]:
        return self._state.positions.get(symbol)

    def remove_position(self, symbol: str) -> None:
        if symbol in self._state.positions:
            logger.info("Removing position", symbol=symbol)
            del self._state.positions[symbol]

    def update_stop(self, symbol: str, new_stop: float) -> None:
        position = self._state.positions.get(symbol)
        if position:
            position.stop_loss = new_stop
            logger.info("Stop loss updated", symbol=symbol, stop_loss=new_stop)

    def update_take_profit(self, symbol: str, new_tp: float) -> None:
        position = self._state.positions.get(symbol)
        if position:
            position.take_profit = new_tp
            logger.info("Take profit updated", symbol=symbol, take_profit=new_tp)


__all__ = ["PortfolioManager", "Position"]
