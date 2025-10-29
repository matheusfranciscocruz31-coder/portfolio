from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(slots=True)
class VolatilitySnapshot:
    atr: float
    atr_pct: float
    realized_vol: float
    structure_break: bool
    volatility_regime: str


def _prepare_dataframe(klines: list[dict[str, Any]]) -> pd.DataFrame:
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


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def realized_volatility(df: pd.DataFrame, window: int = 20) -> pd.Series:
    returns = np.log(df["close"]).diff()
    return returns.rolling(window).std() * np.sqrt(window)


def detect_structure_break(df: pd.DataFrame, lookback: int = 20, threshold: float = 1.5) -> bool:
    closes = df["close"]
    recent = closes.iloc[-1]
    mean = closes.iloc[-lookback:].mean()
    std = closes.iloc[-lookback:].std(ddof=0)
    if std == 0:
        return False
    z_score = (recent - mean) / std
    return abs(z_score) >= threshold


def classify_volatility(atr_pct: float, realized_vol: float) -> str:
    if atr_pct < 0.5 and realized_vol < 0.4:
        return "compressao"
    if atr_pct > 2.0 or realized_vol > 2.5:
        return "explosiva"
    return "normal"


class VolatilityAnalyzer:
    def __init__(self, atr_period: int, structure_threshold: float = 1.8) -> None:
        self._atr_period = atr_period
        self._structure_threshold = structure_threshold

    def analyze(self, klines: list[dict[str, Any]]) -> VolatilitySnapshot:
        df = _prepare_dataframe(klines)
        atr_series = compute_atr(df, self._atr_period)
        latest_atr = float(atr_series.iloc[-1])
        close_price = float(df["close"].iloc[-1])
        atr_pct = (latest_atr / close_price) * 100.0
        rv_series = realized_volatility(df)
        latest_rv = float(rv_series.iloc[-1]) if not rv_series.empty else 0.0
        structure_break = detect_structure_break(df, threshold=self._structure_threshold)
        regime = classify_volatility(atr_pct, latest_rv)

        return VolatilitySnapshot(
            atr=latest_atr,
            atr_pct=atr_pct,
            realized_vol=latest_rv,
            structure_break=structure_break,
            volatility_regime=regime,
        )


__all__ = ["VolatilityAnalyzer", "VolatilitySnapshot"]
