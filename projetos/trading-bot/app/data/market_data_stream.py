from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable

from loguru import logger

from app.exchange.binance_client import BinanceFuturesClient


@dataclass(slots=True)
class MarketEvent:
    symbol: str
    event_type: str
    payload: dict[str, Any]


class MarketDataStream:
    """Coordinates async Binance streams into a unified event queue."""

    def __init__(self, client: BinanceFuturesClient, symbol: str, interval: str, history_limit: int = 500) -> None:
        self._client = client
        self._symbol = symbol.upper()
        self._interval = interval
        self._history_limit = history_limit
        self._queue: asyncio.Queue[MarketEvent] = asyncio.Queue(maxsize=512)
        self._tasks: list[asyncio.Task[Any]] = []
        self._stop = asyncio.Event()

    async def __aenter__(self) -> "MarketDataStream":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    async def start(self) -> None:
        logger.info("Starting market data stream", symbol=self._symbol, interval=self._interval)
        await self._bootstrap_history()
        self._stop.clear()
        self._tasks = [
            asyncio.create_task(self._dispatch_stream("kline", self._client.stream_kline, self._interval)),
            asyncio.create_task(self._dispatch_stream("trade", self._client.stream_trades)),
            asyncio.create_task(self._dispatch_stream("liquidation", self._client.stream_liquidations)),
        ]

    async def stop(self) -> None:
        self._stop.set()
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()

    async def _bootstrap_history(self) -> None:
        klines = await self._client.fetch_klines(self._symbol, self._interval, limit=self._history_limit)
        await self._queue.put(MarketEvent(symbol=self._symbol, event_type="bootstrap_klines", payload={"klines": klines}))

    async def _dispatch_stream(
        self,
        event_type: str,
        stream_factory: Callable[..., AsyncIterator[dict[str, Any]]],
        *args: Any,
    ) -> None:
        try:
            async for msg in stream_factory(self._symbol, *args):
                if self._stop.is_set():
                    break
                event = MarketEvent(symbol=self._symbol, event_type=event_type, payload=msg)
                await self._queue.put(event)
        except asyncio.CancelledError:
            logger.debug("Stream task cancelled", event_type=event_type)
            raise
        except Exception as exc:  # noqa: BLE001 - want full trace for resilience
            logger.exception("Stream dispatch failed", event_type=event_type, error=exc)

    async def events(self) -> AsyncIterator[MarketEvent]:
        while not self._stop.is_set():
            event = await self._queue.get()
            yield event


__all__ = ["MarketDataStream", "MarketEvent"]
