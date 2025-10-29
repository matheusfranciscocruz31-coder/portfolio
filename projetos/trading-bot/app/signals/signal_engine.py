from __future__ import annotations

from dataclasses import dataclass

from app.analysis.order_flow import OrderFlowSnapshot
from app.analysis.volatility import VolatilitySnapshot
from app.strategies.technicals import TechnicalSnapshot


@dataclass(slots=True)
class SignalDecision:
    symbol: str
    direction: str
    confidence: float
    reasons: list[str]


class SignalEngine:
    def __init__(self, weights: dict[str, float]) -> None:
        self._weights = weights

    def evaluate(
        self,
        symbol: str,
        technical: TechnicalSnapshot,
        order_flow: OrderFlowSnapshot,
        volatility: VolatilitySnapshot,
    ) -> SignalDecision:
        reasons: list[str] = []

        trend_weight = self._weights.get("trend_score_weight", 0.4)
        momentum_weight = self._weights.get("momentum_score_weight", 0.25)
        of_weight = self._weights.get("orderflow_score_weight", 0.2)
        liq_weight = self._weights.get("liquidity_score_weight", 0.15)

        trend_component = technical.trend_score * trend_weight
        momentum_component = technical.momentum_score * momentum_weight
        flow_component = order_flow.imbalance * of_weight
        liquidation_component = (-order_flow.liquidation_pressure) * (liq_weight / 2)
        liquidation_component += (0.5 if volatility.structure_break else 0.0)
        if volatility.structure_break:
            reasons.append("Structure break detectada")

        composite = trend_component + momentum_component + flow_component + liquidation_component

        if technical.signal == "long":
            reasons.append("Momentum e tendência favorecem compra")
        elif technical.signal == "short":
            reasons.append("Momentum e tendência favorecem venda")
        else:
            reasons.append("Sinal técnico neutro")

        if order_flow.imbalance > 0.15:
            reasons.append("Fluxo comprador agressivo")
        elif order_flow.imbalance < -0.15:
            reasons.append("Fluxo vendedor agressivo")
        else:
            reasons.append("Order flow neutro")

        if abs(volatility.atr_pct) > 3:
            reasons.append("Alta volatilidade relativa")

        direction = "flat"
        if composite > 0.25:
            direction = "long"
        elif composite < -0.25:
            direction = "short"

        confidence = min(1.0, max(0.0, abs(composite)))

        return SignalDecision(symbol=symbol, direction=direction, confidence=confidence, reasons=reasons)


__all__ = ["SignalEngine", "SignalDecision"]
