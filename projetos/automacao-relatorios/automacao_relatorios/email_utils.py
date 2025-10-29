"""Utilitarios para envio (opcional) de relatorios por e-mail."""

from __future__ import annotations

import json
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class EmailSettings:
    host: str
    port: int
    username: str
    password: str
    sender: str
    recipients: List[str]
    use_tls: bool = True

    @classmethod
    def from_json(cls, path: Path) -> "EmailSettings":
        payload = json.loads(path.read_text(encoding="utf-8"))
        recipients = payload.get("recipients")
        if isinstance(recipients, str):
            recipients = [recipients]
        if not recipients:
            raise ValueError("Lista de destinatarios nao informada.")
        return cls(
            host=payload["host"],
            port=int(payload.get("port", 587)),
            username=payload["username"],
            password=payload["password"],
            sender=payload.get("sender", payload["username"]),
            recipients=list(recipients),
            use_tls=bool(payload.get("use_tls", True)),
        )


def build_email_message(settings: EmailSettings, subject: str, html_body: str, attachments: Optional[Iterable[Path]] = None) -> EmailMessage:
    message = EmailMessage()
    message["From"] = settings.sender
    message["To"] = ", ".join(settings.recipients)
    message["Subject"] = subject
    message.set_content("Versao em HTML disponivel em clientes compatíveis.")
    message.add_alternative(html_body, subtype="html")

    for attachment in attachments or []:
        data = attachment.read_bytes()
        message.add_attachment(
            data,
            maintype="application",
            subtype="octet-stream",
            filename=attachment.name,
        )
    return message


def send_email(settings: EmailSettings, message: EmailMessage) -> None:
    with smtplib.SMTP(settings.host, settings.port) as client:
        if settings.use_tls:
            client.starttls()
        client.login(settings.username, settings.password)
        client.send_message(message)
