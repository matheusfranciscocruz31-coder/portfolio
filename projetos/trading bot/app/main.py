from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    project_root = Path(__file__).resolve().parent.parent
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.append(project_root_str)

from loguru import logger

from app.analysis.order_flow import OrderFlowAnalyzer
from app.analysis.volatility import VolatilityAnalyzer
from app.config import Settings, load_settings
from app.data.market_data_stream import MarketDataStream
from app.exchange.binance_client import BinanceFuturesClient
from app.execution.trade_engine import TradeEngine
from app.portfolio.manager import PortfolioManager
from app.risk.risk_manager import RiskManager
from app.signals.signal_engine import SignalEngine
from app.strategies.technicals import prepare_dataframe, summarize
from app.utils.logging_config import configure_logging


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Binance Futures Auto Trader")
    parser.add_argument("symbol", nargs="?", default=None, help="Par a ser negociado. Ex: BTCUSDT")
    parser.add_argument("--config", dest="config", default=None, help="Caminho para settings.yaml")
    parser.add_argument("--log-level", dest="log_level", default="INFO")
    parser.add_argument("--once", action="store_true", help="Processa apenas um fechamento de candle e encerra")
    return parser.parse_args()


def _prompt_symbol() -> str:
    while True:
        user_input = input("Informe o par a ser negociado (ex: BTCUSDT): ").strip().upper()
        if user_input:
            return user_input
        print("Entrada invalida. Tente novamente.")


def _resolve_symbol(cli_symbol: str | None, settings: Settings) -> tuple[str, str]:
    if cli_symbol:
        return cli_symbol.upper(), "cli"

    if settings.requires_manual_symbol:
        return _prompt_symbol(), "manual"

    raise RuntimeError(
        "Nenhum simbolo informado e receive_command habilitado. "
        "Informe o simbolo via argumento ou configure a integracao de comandos."
    )


async def _handle_events(
    cli_symbol: str | None,
    settings_path: str | None,
    log_level: str,
    run_once: bool,
) -> None:
    settings = load_settings(Path(settings_path) if settings_path else None)
    symbol, source = _resolve_symbol(cli_symbol, settings)
    configure_logging(Path("logs"), log_level)
    logger.info("Symbol definido", symbol=symbol, source=source, receive_command=settings.general.receive_command)

    async with BinanceFuturesClient(
        api_key=settings.credentials.api_key,
        api_secret=settings.credentials.api_secret,
        testnet=settings.is_paper_trading,
    ) as client:
        portfolio = PortfolioManager(settings.general.max_concurrent_positions)
        risk_manager = RiskManager(
            quote_balance=settings.general.quote_balance,
            leverage=settings.general.leverage,
            risk_perc=settings.general.risk_per_trade_pct,
            config=asdict(settings.risk_management),
            fixed_cost=settings.fixed_cost,
        )
        signal_engine = SignalEngine(asdict(settings.signal_weights))
        vol_analyzer = VolatilityAnalyzer(settings.risk_management.atr_period)
        of_analyzer = OrderFlowAnalyzer()
        trade_engine = TradeEngine(client, portfolio, risk_manager, symbol)

        cached_klines: list[list[Any]] = []
        latest_price: float = 0.0

        async with MarketDataStream(client, symbol, settings.general.time_frame, settings.general.data_lookback) as stream:
            async for event in stream.events():
                if event.event_type == "bootstrap_klines":
                    cached_klines = event.payload["klines"]
                    df = prepare_dataframe(cached_klines)
                    latest_price = float(df["close"].iloc[-1])
                    logger.info("Historico inicial carregado", candles=len(cached_klines))
                    continue

                if event.event_type == "trade":
                    payload = event.payload
                    price = float(payload["p"])
                    qty = float(payload["q"])
                    is_buyer_maker = payload["m"]
                    latest_price = price
                    of_analyzer.update_from_trade(price, qty, is_buyer_maker)
                    continue

                if event.event_type == "liquidation":
                    payload = event.payload
                    order = payload.get("o", {})
                    qty = float(order.get("q", 0))
                    side = order.get("S", "BUY")
                    if qty:
                        of_analyzer.update_from_liquidation(qty, side)
                    continue

                if event.event_type == "kline":
                    kline = event.payload.get("k")
                    if not kline:
                        continue
                    closed = kline.get("x", False)
                    latest_price = float(kline["c"])
                    if closed:
                        kline_list = [
                            kline["t"],
                            kline["o"],
                            kline["h"],
                            kline["l"],
                            kline["c"],
                            kline["v"],
                            kline["T"],
                            kline["q"],
                            kline["n"],
                            kline["V"],
                            kline["Q"],
                            "0",
                        ]
                        if cached_klines and cached_klines[-1][0] == kline["t"]:
                            cached_klines[-1] = kline_list
                        else:
                            cached_klines.append(kline_list)
                        if len(cached_klines) > settings.general.data_lookback:
                            cached_klines.pop(0)

                        df = prepare_dataframe(cached_klines)
                        tech_snapshot = summarize(df)
                        vol_snapshot = vol_analyzer.analyze(cached_klines)
                        of_snapshot = of_analyzer.snapshot()

                        decision = signal_engine.evaluate(symbol, tech_snapshot, of_snapshot, vol_snapshot)
                        report = await trade_engine.process_signal(decision, latest_price, vol_snapshot)
                        logger.info(
                            "Decisao processada",
                            direction=decision.direction,
                            confidence=decision.confidence,
                            report=report,
                            reasons=decision.reasons,
                        )
                        if run_once:
                            break


def main() -> None:
    args = _parse_arguments()
    asyncio.run(_handle_events(args.symbol, args.config, args.log_level, args.once))


if __name__ == "__main__":
    main()
