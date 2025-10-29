from __future__ import annotations

import asyncio
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, InvalidOperation, DivisionByZero
from typing import Any, AsyncGenerator

from binance import AsyncClient
try:
    from binance.ws.streams import BinanceSocketManager
except ModuleNotFoundError:
    try:
        from binance.streams import BinanceSocketManager
    except ModuleNotFoundError:
        from binance import BinanceSocketManager  # type: ignore[attr-defined]
try:
    from binance.enums import FuturesType
except (ModuleNotFoundError, ImportError):
    class _FuturesTypeFallback:  # pragma: no cover - only used on legacy installs
        USD_M = "USD_M"
        COIN_M = "COIN_M"

    FuturesType = _FuturesTypeFallback  # type: ignore[assignment]

from loguru import logger

FUTURES_USDM = getattr(FuturesType, "USD_M", "USD_M")


@dataclass(slots=True)
class OrderRequest:
    symbol: str
    side: str
    quantity: float
    order_type: str = "MARKET"
    price: float | None = None
    stop_price: float | None = None
    reduce_only: bool = False
    position_side: str | None = None
    time_in_force: str | None = None


class BinanceFuturesClient:
    """Thin async wrapper around python-binance for futures trading."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self._api_key = api_key
        self._api_secret = api_secret
        self._testnet = testnet
        self._client: AsyncClient | None = None
        self._socket_manager: BinanceSocketManager | None = None
        self._lock = asyncio.Lock()
        self._symbol_filters: dict[str, dict[str, Any]] = {}
        self._dual_position_mode: bool | None = None

    async def __aenter__(self) -> "BinanceFuturesClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def _ensure_client(self) -> AsyncClient:
        async with self._lock:
            if not self._client:
                self._client = await AsyncClient.create(
                    api_key=self._api_key,
                    api_secret=self._api_secret,
                    testnet=self._testnet,
                )
                self._socket_manager = BinanceSocketManager(self._client, max_queue_size=1024)
        return self._client

    async def close(self) -> None:
        async with self._lock:
            if self._socket_manager:
                connections = list(getattr(self._socket_manager, "_conns", {}).values())
                for conn in connections:
                    try:
                        await conn.close()
                    except Exception as exc:  # pragma: no cover - defensive cleanup
                        logger.warning("Failed to close websocket", error=str(exc))
                if hasattr(self._socket_manager, "_conns"):
                    self._socket_manager._conns.clear()
                self._socket_manager = None
            if self._client:
                await self._client.close_connection()
                self._client = None

    async def fetch_klines(self, symbol: str, interval: str, limit: int = 500) -> list[dict[str, Any]]:
        client = await self._ensure_client()
        logger.debug("Fetching klines", symbol=symbol, interval=interval, limit=limit)
        return await client.futures_klines(symbol=symbol.upper(), interval=interval, limit=limit)

    async def fetch_book_ticker(self, symbol: str) -> dict[str, Any]:
        client = await self._ensure_client()
        return await client.futures_symbol_ticker(symbol=symbol.upper())

    async def fetch_position(self, symbol: str) -> dict[str, Any] | None:
        client = await self._ensure_client()
        positions = await client.futures_position_information(symbol=symbol.upper())
        return positions[0] if positions else None

    async def place_order(self, order: OrderRequest) -> dict[str, Any]:
        client = await self._ensure_client()
        params: dict[str, Any] = {
            "symbol": order.symbol.upper(),
            "side": order.side,
            "type": order.order_type,
        }
        if order.reduce_only:
            params["reduceOnly"] = True
        if order.quantity:
            params["quantity"] = order.quantity
        if order.price is not None:
            params["price"] = order.price
        if order.stop_price is not None:
            params["stopPrice"] = order.stop_price
        if order.position_side:
            params["positionSide"] = order.position_side
        if order.time_in_force:
            params["timeInForce"] = order.time_in_force

        try:
            filters = await self._get_symbol_filters(order.symbol)
            self._apply_symbol_filters(order, params, filters)
        except Exception as exc:  # pragma: no cover - sanitize conversion issues
            logger.error(
                "Failed to normalizar parametros de ordem",
                symbol=order.symbol,
                order_type=order.order_type,
                error=str(exc),
            )
            raise

        logger.info("Sending order", **{k: v for k, v in params.items() if k != "symbol"})
        return await client.futures_create_order(**params)

    async def change_leverage(self, symbol: str, leverage: int) -> dict[str, Any]:
        client = await self._ensure_client()
        return await client.futures_change_leverage(symbol=symbol.upper(), leverage=leverage)

    async def uses_dual_position_mode(self) -> bool:
        client = await self._ensure_client()
        if self._dual_position_mode is None:
            try:
                response = await client.futures_get_position_mode()
            except Exception as exc:
                logger.warning("Failed to fetch position mode, assuming one-way", error=str(exc))
                self._dual_position_mode = False
            else:
                self._dual_position_mode = bool(response.get("dualSidePosition", False))
        return bool(self._dual_position_mode)

    async def stream_kline(self, symbol: str, interval: str) -> AsyncGenerator[dict[str, Any], None]:
        await self._ensure_client()
        assert self._socket_manager is not None

        symbol_lc = symbol.lower()
        if hasattr(self._socket_manager, "futures_kline_socket"):
            stream = self._socket_manager.futures_kline_socket(symbol=symbol_lc, interval=interval)
        elif hasattr(self._socket_manager, "futures_multiplex_socket"):
            stream = self._socket_manager.futures_multiplex_socket(
                [f"{symbol_lc}@kline_{interval}"], futures_type=FUTURES_USDM
            )
        else:
            raise AttributeError("BinanceSocketManager lacks a futures kline stream implementation")

        async with stream as socket:
            while True:
                msg = await socket.recv()
                yield self._normalize_stream_payload(msg)

    async def stream_trades(self, symbol: str) -> AsyncGenerator[dict[str, Any], None]:
        await self._ensure_client()
        assert self._socket_manager is not None

        symbol_lc = symbol.lower()
        if hasattr(self._socket_manager, "aggtrade_futures_socket"):
            stream = self._socket_manager.aggtrade_futures_socket(symbol_lc, futures_type=FUTURES_USDM)
        elif hasattr(self._socket_manager, "futures_aggtrade_socket"):
            stream = self._socket_manager.futures_aggtrade_socket(symbol=symbol_lc)
        elif hasattr(self._socket_manager, "futures_multiplex_socket"):
            stream = self._socket_manager.futures_multiplex_socket(
                [f"{symbol_lc}@aggTrade"], futures_type=FUTURES_USDM
            )
        else:
            raise AttributeError("BinanceSocketManager lacks a futures aggtrade stream implementation")

        async with stream as socket:
            while True:
                msg = await socket.recv()
                yield self._normalize_stream_payload(msg)

    async def stream_liquidations(
        self, symbol: str | None = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        await self._ensure_client()
        assert self._socket_manager is not None

        if hasattr(self._socket_manager, "futures_liquidation_socket"):
            stream = self._socket_manager.futures_liquidation_socket(
                symbol=symbol.lower() if symbol else None
            )
        elif hasattr(self._socket_manager, "futures_multiplex_socket"):
            streams = [f"{symbol.lower()}@forceOrder"] if symbol else ["!forceOrder@arr"]
            stream = self._socket_manager.futures_multiplex_socket(streams, futures_type=FUTURES_USDM)
        else:
            raise AttributeError("BinanceSocketManager lacks a futures liquidation stream implementation")

        async with stream as socket:
            while True:
                msg = await socket.recv()
                yield self._normalize_stream_payload(msg)

    async def _get_symbol_filters(self, symbol: str) -> dict[str, Any]:
        symbol_key = symbol.upper()
        cached = self._symbol_filters.get(symbol_key)
        if cached:
            return cached

        client = await self._ensure_client()
        info = await client.futures_exchange_info()
        symbols = info.get("symbols", [])
        for symbol_info in symbols:
            filters = {f.get("filterType"): f for f in symbol_info.get("filters", [])}
            self._symbol_filters[symbol_info.get("symbol", "")] = filters

        cached = self._symbol_filters.get(symbol_key)
        if not cached:
            raise ValueError(f"Symbol {symbol_key} not found in futures exchange info")
        return cached

    def _apply_symbol_filters(self, order: OrderRequest, params: dict[str, Any], filters: dict[str, Any]) -> None:
        lot_filter = self._select_lot_filter(filters, order.order_type)
        quantity_value = params.get("quantity")
        if quantity_value is not None and lot_filter:
            step = lot_filter.get("stepSize")
            min_qty = lot_filter.get("minQty")
            qty = self._round_to_step(quantity_value, step)
            if qty <= 0:
                raise ValueError(f"Quantidade invalida apos ajuste: {quantity_value}")
            if min_qty is not None and qty < self._to_decimal(min_qty):
                raise ValueError(
                    f"Quantidade {qty} menor que minimo {min_qty} para {order.symbol.upper()}"
                )
            params["quantity"] = self._format_decimal(qty)
            order.quantity = float(qty)

        price_filter = filters.get("PRICE_FILTER")
        if price_filter:
            tick_size = price_filter.get("tickSize")
            min_price = price_filter.get("minPrice")
            max_price = price_filter.get("maxPrice")
        else:
            tick_size = min_price = max_price = None

        attr_map = {"price": "price", "stopPrice": "stop_price"}
        for key, attr_name in attr_map.items():
            value = params.get(key)
            if value is None:
                continue
            if tick_size:
                price = self._round_to_step(value, tick_size)
                if min_price is not None and price < self._to_decimal(min_price):
                    price = self._to_decimal(min_price)
                if max_price is not None and price > self._to_decimal(max_price):
                    price = self._to_decimal(max_price)
            else:
                price = self._to_decimal(value)
            params[key] = self._format_decimal(price)
            setattr(order, attr_name, float(price))

        for key in ("quantity", "price", "stopPrice"):
            value = params.get(key)
            if value is None:
                continue
            if not isinstance(value, str):
                params[key] = self._format_decimal(self._to_decimal(value))

        for key in list(params.keys()):
            if params[key] is None:
                del params[key]

    @staticmethod
    def _select_lot_filter(filters: dict[str, Any], order_type: str) -> dict[str, Any] | None:
        market_like = {"MARKET", "STOP_MARKET", "TAKE_PROFIT_MARKET"}
        if order_type.upper() in market_like:
            return filters.get("MARKET_LOT_SIZE") or filters.get("LOT_SIZE")
        return filters.get("LOT_SIZE") or filters.get("MARKET_LOT_SIZE")

    @staticmethod
    def _round_to_step(value: Any, step: Any) -> Decimal:
        if value is None:
            raise ValueError("Valor ausente para ajuste de precisao")
        dec_value = BinanceFuturesClient._to_decimal(value)
        if step in {None, "0", 0}:
            return dec_value
        dec_step = BinanceFuturesClient._to_decimal(step)
        if dec_step <= 0:
            return dec_value
        try:
            quantized = (dec_value // dec_step) * dec_step
            return quantized.quantize(dec_step, rounding=ROUND_DOWN).normalize()
        except (InvalidOperation, DivisionByZero):  # type: ignore[name-defined]
            logger.error("Falha ao ajustar valor", value=str(value), step=str(step))
            raise

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        if value is None:
            raise ValueError("Valor None nao pode ser convertido para Decimal")
        return Decimal(str(value))

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        normalized = value.normalize()
        string = format(normalized, "f")
        if "." in string:
            string = string.rstrip("0").rstrip(".")
        return string or "0"

    @staticmethod
    def _normalize_stream_payload(message: Any) -> dict[str, Any]:
        if isinstance(message, dict):
            if message.get("e") == "error":
                err_type = message.get("type", "unknown")
                err_msg = message.get("m", "")
                raise RuntimeError(f"Stream error: {err_type} - {err_msg}")
            if "data" in message and isinstance(message["data"], dict):
                return message["data"]
        return message


__all__ = ["BinanceFuturesClient", "OrderRequest"]







