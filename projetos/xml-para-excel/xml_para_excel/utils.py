"""Funcoes auxiliares para conversao."""

from __future__ import annotations

import datetime as dt
import re
from typing import Optional


def to_float(value: Optional[str]) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return 0.0


def clean_digits(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\D+", "", value)


def normalise_key(chave: Optional[str]) -> str:
    digits = clean_digits(chave)
    if len(digits) == 44:
        return digits
    return digits[:44]


def parse_datetime(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "")).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return value
