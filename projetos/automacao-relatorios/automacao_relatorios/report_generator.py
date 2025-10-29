"""Geracao de relatorios Excel/PDF a partir de arquivos de vendas."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
from jinja2 import Template

from .validation import ValidationResult, validate_dataset


@dataclass
class ReportOutput:
    excel_path: Optional[Path] = None
    pdf_path: Optional[Path] = None
    email_path: Optional[Path] = None
    issues: List[str] = None


def _load_sources(input_path: Path) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for file in sorted(input_path.iterdir()):
        if file.suffix.lower() in {".csv", ".txt"}:
            frames.append(pd.read_csv(file))
        elif file.suffix.lower() in {".xlsx", ".xls"}:
            frames.append(pd.read_excel(file))
    if not frames:
        raise FileNotFoundError("Nenhum arquivo CSV ou XLSX encontrado em {}".format(input_path))
    return pd.concat(frames, ignore_index=True)


def _kpi_snapshot(frame: pd.DataFrame) -> Dict[str, float]:
    total_receita = float(frame["valor"].sum())
    volume = int(frame["quantidade"].sum())
    ticket = float(total_receita / volume) if volume else 0.0
    clientes = frame["cliente"].nunique()
    produtos = frame["produto"].nunique()
    return {
        "total_receita": total_receita,
        "volume": volume,
        "ticket_medio": ticket,
        "clientes": clientes,
        "produtos": produtos,
    }


def _pivot_by(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    grouped = (
        frame.groupby(column)
        .agg({"quantidade": "sum", "valor": "sum"})
        .sort_values(by="valor", ascending=False)
    )
    grouped["ticket_medio"] = grouped["valor"] / grouped["quantidade"].replace(0, 1)
    return grouped.reset_index()


def _pivot_by_period(frame: pd.DataFrame) -> pd.DataFrame:
    temp = frame.copy()
    temp["periodo"] = pd.to_datetime(temp["data"]).dt.to_period("M").astype(str)
    grouped = (
        temp.groupby("periodo")
        .agg({"quantidade": "sum", "valor": "sum"})
        .sort_values(by="periodo")
        .reset_index()
    )
    grouped["ticket_medio"] = grouped["valor"] / grouped["quantidade"].replace(0, 1)
    return grouped


def _render_html(kpis: Dict[str, float], tabela_produtos: pd.DataFrame, tabela_clientes: pd.DataFrame, tabela_periodos: pd.DataFrame, issues: Iterable[str]) -> str:
    template = Template(
        """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: Arial, sans-serif; color: #1f2933; }
    h1 { color: #0f172a; }
    .cards { display: flex; gap: 16px; margin-bottom: 16px; }
    .card { border: 1px solid #cbd5e1; padding: 12px; border-radius: 8px; background: #f8fafc; flex: 1; }
    table { border-collapse: collapse; width: 100%; margin-bottom: 16px; }
    th, td { border: 1px solid #e2e8f0; padding: 8px; text-align: left; }
    th { background: #f1f5f9; }
    .issues { color: #b91c1c; }
  </style>
</head>
<body>
  <h1>Resumo de desempenho comercial</h1>
  <div class="cards">
    {% for titulo, valor in cards %}
    <div class="card">
      <h2>{{ titulo }}</h2>
      <p><strong>{{ valor }}</strong></p>
    </div>
    {% endfor %}
  </div>
  <h2>Top produtos</h2>
  {{ tabela_produtos.to_html(index=False, justify="left", border=0) }}
  <h2>Top clientes</h2>
  {{ tabela_clientes.to_html(index=False, justify="left", border=0) }}
  <h2>Evolucao por periodo</h2>
  {{ tabela_periodos.to_html(index=False, justify="left", border=0) }}
  <h2>Logs</h2>
  <ul class="issues">
    {% for item in issues %}
      <li>{{ item }}</li>
    {% endfor %}
  </ul>
</body>
</html>
        """
    )
    cards = [
        ("Receita total", f"R$ {kpis['total_receita']:,.2f}"),
        ("Volume vendido", kpis["volume"]),
        ("Ticket medio", f"R$ {kpis['ticket_medio']:,.2f}"),
        ("Clientes ativos", kpis["clientes"]),
        ("Produtos ativos", kpis["produtos"]),
    ]
    return template.render(
        cards=cards,
        tabela_produtos=tabela_produtos,
        tabela_clientes=tabela_clientes,
        tabela_periodos=tabela_periodos,
        issues=issues,
    )


def _write_excel(path: Path, kpis: Dict[str, float], tabela_produtos: pd.DataFrame, tabela_clientes: pd.DataFrame, tabela_periodos: pd.DataFrame, frame: pd.DataFrame, issues: Iterable[str]) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        resumo = pd.DataFrame(
            [
                {"indicador": "Receita total", "valor": kpis["total_receita"]},
                {"indicador": "Volume vendido", "valor": kpis["volume"]},
                {"indicador": "Ticket medio", "valor": kpis["ticket_medio"]},
                {"indicador": "Clientes ativos", "valor": kpis["clientes"]},
                {"indicador": "Produtos ativos", "valor": kpis["produtos"]},
            ]
        )
        resumo.to_excel(writer, sheet_name="Indicadores", index=False)
        tabela_produtos.to_excel(writer, sheet_name="Produtos", index=False)
        tabela_clientes.to_excel(writer, sheet_name="Clientes", index=False)
        tabela_periodos.to_excel(writer, sheet_name="Periodo", index=False)
        frame.to_excel(writer, sheet_name="Detalhe", index=False)
        pd.DataFrame({"observacoes": list(issues)}).to_excel(writer, sheet_name="Observacoes", index=False)


def _write_pdf(path: Path, html: str) -> Optional[str]:
    try:
        import pdfkit  # type: ignore
    except Exception:
        return "Biblioteca pdfkit nao encontrada; PDF nao gerado."

    try:
        pdfkit.from_string(html, str(path))
        return None
    except OSError:
        return "wkhtmltopdf nao disponivel no sistema; PDF nao gerado."


def _write_email(path: Path, html: str, kpis: Dict[str, float]) -> None:
    assunto = "Resumo de vendas - receita R$ {:.2f}".format(kpis["total_receita"])
    corpo = f"""Subject: {assunto}
MIME-Version: 1.0
Content-Type: text/html; charset=UTF-8

{html}
"""
    path.write_text(corpo, encoding="utf-8")


def build_report_bundle(input_dir: Path, output_dir: Path, formatos: Iterable[str], janela: str = "") -> ReportOutput:
    """Fluxo principal."""

    formatos = {f.lower() for f in formatos}
    output_dir.mkdir(parents=True, exist_ok=True)

    frame_raw = _load_sources(input_dir)
    validation: ValidationResult = validate_dataset(frame_raw, janela)
    frame = validation.frame

    kpis = _kpi_snapshot(frame)
    tabela_produtos = _pivot_by(frame, "produto").head(10)
    tabela_clientes = _pivot_by(frame, "cliente").head(10)
    tabela_periodos = _pivot_by_period(frame)
    html = _render_html(kpis, tabela_produtos, tabela_clientes, tabela_periodos, validation.issues)

    result = ReportOutput(issues=validation.issues.copy())

    if "excel" in formatos:
        excel_path = output_dir / "relatorio_resumo.xlsx"
        _write_excel(excel_path, kpis, tabela_produtos, tabela_clientes, tabela_periodos, frame, validation.issues)
        result.excel_path = excel_path

    if "pdf" in formatos:
        pdf_path = output_dir / "relatorio_resumo.pdf"
        message = _write_pdf(pdf_path, html)
        if message:
            result.issues.append(message)
        else:
            result.pdf_path = pdf_path

    if "email" in formatos:
        email_path = output_dir / "resumo_email.eml"
        _write_email(email_path, html, kpis)
        result.email_path = email_path

    return result
