from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from app.analysis.volatility import VolatilitySnapshot
from app.exchange.binance_client import BinanceFuturesClient, OrderRequest
from app.portfolio.manager import PortfolioManager, Position
from app.risk.risk_manager import PositionSizing, RiskManager
from app.signals.signal_engine import SignalDecision


@dataclass(slots=True)
class ExecutionReport:
    opened: bool = False
    closed: bool = False
    adjusted: bool = False
    message: str = ""


class TradeEngine:
    def __init__(
        self,
        client: BinanceFuturesClient,
        portfolio: PortfolioManager,
        risk_manager: RiskManager,
        symbol: str,
    ) -> None:
        self._client = client
        self._portfolio = portfolio
        self._risk = risk_manager
        self._symbol = symbol.upper()
        self._leverage_synced = False
        self._dual_side_position: bool | None = None

    async def _ensure_leverage(self) -> None:
        if not self._leverage_synced:
            response = await self._client.change_leverage(self._symbol, self._risk.leverage)  # noqa: SLF001
            logger.info("Leverage sync", response=response)
            self._leverage_synced = True

    async def _is_dual_position_mode(self) -> bool:
        if self._dual_side_position is None:
            self._dual_side_position = await self._client.uses_dual_position_mode()
        return bool(self._dual_side_position)

    async def _position_side_for(self, direction: str) -> str | None:
        if direction not in {"long", "short"}:
            return None
        if not await self._is_dual_position_mode():
            return None
        return "LONG" if direction == "long" else "SHORT"

    async def process_signal(self, decision: SignalDecision, price: float, volatility: VolatilitySnapshot) -> ExecutionReport:
        await self._ensure_leverage()
        position = self._portfolio.get_position(self._symbol)

        if decision.direction == "flat":
            if position:
                await self._close_position(position)
                self._portfolio.remove_position(self._symbol)
                return ExecutionReport(closed=True, message="Fechando posicao por sinal neutro")
            return ExecutionReport(message="Nada a fazer - sinal neutro")

        if position:
            if position.direction != decision.direction:
                await self._close_position(position)
                self._portfolio.remove_position(self._symbol)
                return ExecutionReport(closed=True, message="Reversao de posicao")
            return ExecutionReport(message="Mantendo posicao atual")

        if not self._portfolio.can_open(self._symbol):
            return ExecutionReport(message="Limite de posicoes atingido")

        sizing = self._risk.size_position(price, volatility, decision.direction)
        if sizing.quantity <= 0:
            return ExecutionReport(message="Tamanho de posicao invalido")

        await self._open_position(decision.direction, sizing)
        new_position = Position(
            symbol=self._symbol,
            direction=decision.direction,
            entry_price=price,
            quantity=sizing.quantity,
            stop_loss=sizing.stop_loss,
            take_profit=sizing.take_profit,
            trailing_active=sizing.trailing_active,
            notional=sizing.notional,
            cost=sizing.cost,
        )
        self._portfolio.add_position(new_position)
        return ExecutionReport(opened=True, message="Posicao aberta")

    async def _open_position(self, direction: str, sizing: PositionSizing) -> None:
        side = "BUY" if direction == "long" else "SELL"
        position_side = await self._position_side_for(direction)
        order = OrderRequest(
            symbol=self._symbol,
            side=side,
            quantity=sizing.quantity,
            position_side=position_side,
        )
        await self._client.place_order(order)
        sizing.quantity = order.quantity
        await self._place_protection_orders(direction, sizing)

    async def _close_position(self, position: Position) -> None:
        side = "SELL" if position.direction == "long" else "BUY"
        position_side = await self._position_side_for(position.direction)
        reduce_only = position_side is None
        order = OrderRequest(
            symbol=self._symbol,
            side=side,
            quantity=position.quantity,
            reduce_only=reduce_only,
            position_side=position_side,
        )
        await self._client.place_order(order)

    async def _place_protection_orders(self, direction: str, sizing: PositionSizing) -> None:
        stop_side = "SELL" if direction == "long" else "BUY"
        tp_side = "SELL" if direction == "long" else "BUY"
        position_side = await self._position_side_for(direction)
        reduce_only = position_side is None

        stop_order = OrderRequest(
            symbol=self._symbol,
            side=stop_side,
            order_type="STOP_MARKET",
            stop_price=sizing.stop_loss,
            quantity=sizing.quantity,
            reduce_only=reduce_only,
            position_side=position_side,
        )
        take_profit_order = OrderRequest(
            symbol=self._symbol,
            side=tp_side,
            order_type="TAKE_PROFIT_MARKET",
            stop_price=sizing.take_profit,
            quantity=sizing.quantity,
            reduce_only=reduce_only,
            position_side=position_side,
        )
        await self._client.place_order(stop_order)
        sizing.stop_loss = stop_order.stop_price or sizing.stop_loss
        await self._client.place_order(take_profit_order)
        sizing.take_profit = take_profit_order.stop_price or sizing.take_profit


__all__ = ["TradeEngine", "ExecutionReport"]










