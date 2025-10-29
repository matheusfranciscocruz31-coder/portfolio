from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class Credentials:
    api_key: str
    api_secret: str


@dataclass(slots=True)
class GeneralSettings:
    base_asset: str
    trading_mode: str
    quote_balance: float
    leverage: int
    risk_per_trade_pct: float
    max_concurrent_positions: int
    time_frame: str
    data_lookback: int
    receive_command: bool = True
    fixed_cost: float = 0.0


@dataclass(slots=True)
class Filters:
    min_volume_usdt: float
    max_spread_pct: float


@dataclass(slots=True)
class RiskManagement:
    atr_period: int
    atr_multiplier_sl: float
    atr_multiplier_tp: float
    trailing_stop: bool
    trailing_atr_multiplier: float


@dataclass(slots=True)
class SignalWeights:
    trend_score_weight: float
    momentum_score_weight: float
    orderflow_score_weight: float
    liquidity_score_weight: float


@dataclass(slots=True)
class Notifications:
    enabled: bool
    webhook_url: str


@dataclass(slots=True)
class Settings:
    credentials: Credentials
    general: GeneralSettings
    filters: Filters
    risk_management: RiskManagement
    signal_weights: SignalWeights
    notifications: Notifications

    @property
    def is_paper_trading(self) -> bool:
        return self.general.trading_mode.lower() != "live"

    @property
    def requires_manual_symbol(self) -> bool:
        return not self.general.receive_command

    @property
    def fixed_cost(self) -> float:
        return max(self.general.fixed_cost, 0.0)


_DEFAULT_PATH = Path("config") / "settings.yaml"
_EXAMPLE_PATH = Path("config") / "settings.example.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        return yaml.safe_load(fp) or {}


def load_settings(path: Path | None = None) -> Settings:
    """Load configuration from YAML, falling back to example template."""
    config_path = path or _DEFAULT_PATH

    if not config_path.exists():
        if _EXAMPLE_PATH.exists():
            raise FileNotFoundError(
                f"Arquivo de configuracao {config_path} nao encontrado. Copie {_EXAMPLE_PATH} e ajuste as credenciais."
            )
        raise FileNotFoundError(f"Arquivo de configuracao {config_path} nao encontrado.")

    raw = _load_yaml(config_path)

    try:
        credentials_raw = raw["credentials"]
        general_raw = raw["general"]
        filters_raw = raw["filters"]
        risk_raw = raw["risk_management"]
        weights_raw = raw["signal_weights"]
        notifications_raw = raw["notifications"]
    except KeyError as exc:
        missing = exc.args[0]
        raise KeyError(f"Secao '{missing}' ausente em {config_path}.") from exc

    general = dict(general_raw)
    general.setdefault("receive_command", True)
    general.setdefault("fixed_cost", 0.0)

    return Settings(
        credentials=Credentials(**credentials_raw),
        general=GeneralSettings(**general),
        filters=Filters(**filters_raw),
        risk_management=RiskManagement(**risk_raw),
        signal_weights=SignalWeights(**weights_raw),
        notifications=Notifications(**notifications_raw),
    )


__all__ = ["Settings", "load_settings", "Credentials", "GeneralSettings"]



