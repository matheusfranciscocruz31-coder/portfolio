"""Interface de linha de comando para automatizar relatorios."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from automacao_relatorios import EmailSettings, build_email_message, build_report_bundle


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automacao de relatorios de vendas.")
    parser.add_argument("--input", type=Path, required=True, help="Diretorio com CSV/XLSX de entrada.")
    parser.add_argument("--output", type=Path, required=True, help="Diretorio para salvar resultados.")
    parser.add_argument(
        "--formato",
        nargs="+",
        default=["excel"],
        help="Formatos desejados: excel, pdf, email.",
    )
    parser.add_argument(
        "--janela",
        choices=["diaria", "semanal", "mensal"],
        default="mensal",
        help="Filtro temporal aplicado antes do consolidado.",
    )
    parser.add_argument(
        "--smtp-config",
        type=Path,
        help="Arquivo JSON com credenciais SMTP para disparo do e-mail (opcional).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    input_dir: Path = args.input
    output_dir: Path = args.output

    if not input_dir.exists():
        print(f"[ERRO] Diretorio de entrada inexistente: {input_dir}")
        return 2

    try:
        bundle = build_report_bundle(
            input_dir=input_dir,
            output_dir=output_dir,
            formatos=args.formato,
            janela=args.janela,
        )
    except Exception as exc:
        print(f"[ERRO] Falha durante processamento: {exc}")
        return 1

    print("[OK] Relatorio gerado.")
    if bundle.excel_path:
        print(f" - Excel: {bundle.excel_path}")
    if bundle.pdf_path:
        print(f" - PDF: {bundle.pdf_path}")
    if bundle.email_path:
        print(f" - Email: {bundle.email_path}")

    for issue in bundle.issues or []:
        print(f"[LOG] {issue}")

    if "email" in {f.lower() for f in args.formato} and args.smtp_config:
        try:
            settings = EmailSettings.from_json(args.smtp_config)
            if bundle.email_path:
                html = bundle.email_path.read_text(encoding="utf-8").split("\n\n", 1)[-1]
            else:
                html = ""
            attachments = [path for path in [bundle.excel_path, bundle.pdf_path] if path]
            message = build_email_message(
                settings=settings,
                subject="Resumo de vendas automatizado",
                html_body=html,
                attachments=attachments,
            )
            from automacao_relatorios.email_utils import send_email

            send_email(settings, message)
            print("[OK] Email enviado com sucesso.")
        except Exception as exc:
            print(f"[ALERTA] Nao foi possivel enviar o email: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
