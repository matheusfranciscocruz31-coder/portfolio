"""Conversao de NF-e XML para planilha Excel."""

from __future__ import annotations

import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

from .parser import NotaFiscal, parse_nfe

LOGGER = logging.getLogger("xml_para_excel")


def collect_documents(source: Path) -> List[Path]:
    """Coleta arquivos XML a partir de arquivo ou pasta."""

    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"Origem nao encontrada: {source}")

    if source.is_file() and source.suffix.lower() == ".xml":
        return [source]

    documents: List[Path] = []
    if source.is_file() and source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as zf, tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            zf.extractall(tmp_path)
            for xml in tmp_path.rglob("*.xml"):
                documents.append(xml)
        return documents

    if source.is_dir():
        documents.extend(sorted(source.rglob("*.xml")))
    else:
        raise ValueError(f"Formato nao suportado: {source.suffix}")

    if not documents:
        raise FileNotFoundError("Nenhum XML encontrado.")
    return documents


def _resumo_dataframe(notas: Iterable[NotaFiscal]) -> pd.DataFrame:
    rows = []
    for nota in notas:
        rows.append(
            {
                "chave": nota.chave,
                "numero": nota.numero,
                "serie": nota.serie,
                "emitente": nota.emitente_nome,
                "emitente_cnpj": nota.emitente_cnpj,
                "destinatario": nota.destinatario_nome,
                "destinatario_doc": nota.destinatario_doc,
                "data_emissao": nota.data_emissao,
                "valor_total": nota.valor_total,
                "icms_total": nota.icms_total,
                "arquivo": str(nota.arquivo) if nota.arquivo else "",
            }
        )
    return pd.DataFrame(rows)


def _itens_dataframe(notas: Iterable[NotaFiscal]) -> pd.DataFrame:
    rows = []
    for nota in notas:
        for item in nota.itens:
            rows.append(
                {
                    "chave": nota.chave,
                    "n_item": item.numero,
                    "codigo": item.codigo,
                    "descricao": item.descricao,
                    "cfop": item.cfop,
                    "ncm": item.ncm,
                    "unidade": item.unidade,
                    "quantidade": item.quantidade,
                    "valor_unitario": item.valor_unitario,
                    "valor_total": item.valor_total,
                    "icms": item.icms,
                    "ipi": item.ipi,
                }
            )
    return pd.DataFrame(rows)


def _pagamentos_dataframe(notas: Iterable[NotaFiscal]) -> pd.DataFrame:
    rows = []
    for nota in notas:
        for pagamento in nota.pagamentos:
            rows.append(
                {
                    "chave": nota.chave,
                    "forma": pagamento.forma,
                    "valor": pagamento.valor,
                }
            )
    return pd.DataFrame(rows)


def build_workbook(
    documentos: Iterable[Path],
    output_dir: Path,
    arquivo: str = "notas.xlsx",
    normalizar: bool = True,
    dry_run: bool = False,
) -> dict:
    """Gera planilha consolidada a partir de uma lista de XMLs."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    notas: List[NotaFiscal] = []
    issues: List[str] = []

    for xml_path in documentos:
        try:
            nota = parse_nfe(xml_path, normalizar=normalizar)
            notas.append(nota)
        except Exception as exc:
            message = f"Falha ao processar {xml_path.name}: {exc}"
            LOGGER.error(message)
            issues.append(message)

    if dry_run:
        return {"notas": len(notas), "issues": issues, "arquivo": None}

    if not notas:
        raise RuntimeError("Nenhuma nota valida para exportar.")

    resumo_df = _resumo_dataframe(notas)
    itens_df = _itens_dataframe(notas)
    pagamentos_df = _pagamentos_dataframe(notas)

    excel_path = output_dir / arquivo
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        resumo_df.to_excel(writer, sheet_name="Resumo", index=False)
        itens_df.to_excel(writer, sheet_name="Itens", index=False)
        pagamentos_df.to_excel(writer, sheet_name="Pagamentos", index=False)

    if issues:
        log_path = output_dir / "processamento.log"
        log_path.write_text("\n".join(issues), encoding="utf-8")

    return {"notas": len(notas), "issues": issues, "arquivo": excel_path}
