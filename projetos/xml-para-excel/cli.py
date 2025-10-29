"""Interface de linha de comando para o conversor XML -> Excel."""

from __future__ import annotations

from pathlib import Path

import typer

from xml_para_excel.converter import build_workbook, collect_documents

app = typer.Typer(add_completion=False, help="Converte NF-e XML para planilha Excel.")


@app.command()
def main(
    input: Path = typer.Option(..., "--input", "-i", help="Arquivo XML ou pasta com XMLs."),
    output: Path = typer.Option(Path("output"), "--output", "-o", help="Diretorio de destino."),
    arquivo: str = typer.Option("notas.xlsx", "--arquivo", "-a", help="Nome do arquivo Excel."),
    normalizar: bool = typer.Option(True, "--normalizar/--sem-normalizar", help="Limpa chaves e documentos."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Apenas valida os arquivos."),
) -> None:
    try:
        docs = collect_documents(input)
    except Exception as exc:
        typer.echo(f"[ERRO] {exc}")
        raise typer.Exit(code=1) from exc

    result = build_workbook(docs, output, arquivo=arquivo, normalizar=normalizar, dry_run=dry_run)
    typer.echo(f"[OK] Notas processadas: {result['notas']}")
    if result["arquivo"]:
        typer.echo(f" - Excel: {result['arquivo']}")
    if result["issues"]:
        typer.echo("Alertas:")
        for issue in result["issues"]:
            typer.echo(f"  - {issue}")


if __name__ == "__main__":
    app()
