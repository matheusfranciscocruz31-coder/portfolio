"""
Pacote principal para a automacao de relatorios.

Expose funcoes chave para reuso por scripts externos.
"""

from .report_generator import build_report_bundle
from .email_utils import EmailSettings, build_email_message

__all__ = [
    "build_report_bundle",
    "EmailSettings",
    "build_email_message",
]
