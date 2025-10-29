from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import EMAIndicator, MACD
from ta.volatility import BollingerBands


@dataclass(slots=True)
class TechnicalSnapshot:
    trend_score: float
    momentum_score: float
    structure_bias: float
    signal: str


def _normalize(value: float, lower: float, upper: float) -> float:
    return (value - lower) / (upper - lower) if upper != lower else 0.0


def _trend_score(df: pd.DataFrame) -> float:
    ema_fast = EMAIndicator(df["close"], window=21).ema_indicator()
    ema_slow = EMAIndicator(df["close"], window=55).ema_indicator()
    ema_fast_valid = ema_fast.dropna()
    slope = 0.0
    if len(ema_fast_valid) > 1:
        slope = np.polyfit(range(len(ema_fast_valid)), ema_fast_valid, deg=1)[0]
    crossover = 0.0
    if ema_slow.iloc[-1] != 0:
        crossover = (ema_fast.iloc[-1] - ema_slow.iloc[-1]) / ema_slow.iloc[-1]
    return float(np.tanh(crossover * 10 + slope))


def _momentum_score(df: pd.DataFrame) -> float:
    rsi = RSIIndicator(df["close"], window=14).rsi()
    stoch = StochasticOscillator(df["high"], df["low"], df["close"], window=14).stoch()
    latest_rsi = float(rsi.iloc[-1])
    latest_stoch = float(stoch.iloc[-1])
    rsi_score = _normalize(latest_rsi, 0, 100) * 2 - 1
    stoch_score = _normalize(latest_stoch, 0, 100) * 2 - 1
    return float((rsi_score + stoch_score) / 2)


def _structure_bias(df: pd.DataFrame) -> float:
    macd = MACD(df["close"], window_slow=26, window_fast=12, window_sign=9)
    macd_hist = float(macd.macd_diff().iloc[-1])
    bb = BollingerBands(df["close"], window=20, window_dev=2)
    mid = bb.bollinger_mavg().iloc[-1]
    hband = bb.bollinger_hband().iloc[-1]
    std = (hband - mid) / 2 if hband != mid else 0.0
    if std == 0:
        z_score = 0.0
    else:
        z_score = (df["close"].iloc[-1] - mid) / std
    return float(np.tanh(macd_hist * 5 + z_score))


def summarize(df: pd.DataFrame) -> TechnicalSnapshot:
    trend = _trend_score(df)
    momentum = _momentum_score(df)
    structure = _structure_bias(df)
    composite = 0.5 * trend + 0.3 * momentum + 0.2 * structure
    if composite > 0.2:
        signal = "long"
    elif composite < -0.2:
        signal = "short"
    else:
        signal = "neutral"
    return TechnicalSnapshot(trend_score=trend, momentum_score=momentum, structure_bias=structure, signal=signal)


def prepare_dataframe(klines: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(klines, columns=[
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_volume",
        "trades",
        "taker_buy_base",
        "taker_buy_quote",
        "ignore",
    ])
    numeric_cols = ["open", "high", "low", "close", "volume", "quote_volume"]
    frame[numeric_cols] = frame[numeric_cols].astype(float)
    frame["open_time"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
    frame.set_index("open_time", inplace=True)
    return frame


__all__ = ["prepare_dataframe", "summarize", "TechnicalSnapshot"]
