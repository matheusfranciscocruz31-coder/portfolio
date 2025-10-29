"""Parser de arquivos NF-e XML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from lxml import etree

from .utils import clean_digits, normalise_key, parse_datetime, to_float

NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}


def _text(node, path: str) -> str:
    if node is None:
        return ""
    element = node.find(path, namespaces=NS)
    return element.text.strip() if element is not None and element.text else ""


@dataclass
class Item:
    numero: int
    codigo: str
    descricao: str
    cfop: str
    ncm: str
    unidade: str
    quantidade: float
    valor_unitario: float
    valor_total: float
    icms: float
    ipi: float


@dataclass
class Pagamento:
    forma: str
    valor: float


@dataclass
class NotaFiscal:
    chave: str
    numero: str
    serie: str
    emitente_nome: str
    emitente_cnpj: str
    destinatario_nome: str
    destinatario_doc: str
    data_emissao: str
    valor_total: float
    icms_total: float
    arquivo: Path | None = None
    itens: List[Item] = field(default_factory=list)
    pagamentos: List[Pagamento] = field(default_factory=list)


def parse_nfe(xml_path: Path, normalizar: bool = True) -> NotaFiscal:
    tree = etree.parse(str(xml_path))
    root = tree.getroot()
    inf = root.find(".//nfe:infNFe", namespaces=NS)
    if inf is None:
        raise ValueError("Estrutura NFe nao encontrada.")

    chave = normalise_key(inf.get("Id")) if normalizar else (inf.get("Id") or "")

    emit = inf.find("nfe:emit", namespaces=NS)
    dest = inf.find("nfe:dest", namespaces=NS)
    total = inf.find("nfe:total/nfe:ICMSTot", namespaces=NS)
    ide = inf.find("nfe:ide", namespaces=NS)

    emitente_nome = _text(emit, "nfe:xNome") if emit is not None else ""
    emitente_cnpj = clean_digits(_text(emit, "nfe:CNPJ")) if normalizar else _text(emit, "nfe:CNPJ")

    destinatario_nome = _text(dest, "nfe:xNome") if dest is not None else ""
    dest_doc = _text(dest, "nfe:CNPJ") or _text(dest, "nfe:CPF") if dest is not None else ""
    destinatario_doc = clean_digits(dest_doc) if normalizar else dest_doc

    numero = _text(ide, "nfe:nNF")
    serie = _text(ide, "nfe:serie")
    emissao = parse_datetime(_text(ide, "nfe:dhEmi")) if normalizar else _text(ide, "nfe:dhEmi")

    valor_total = to_float(_text(total, "nfe:vNF") if total is not None else "")
    icms_total = to_float(_text(total, "nfe:vICMS") if total is not None else "")

    itens: List[Item] = []
    for det in inf.findall("nfe:det", namespaces=NS):
        numero_item = int(det.get("nItem", "0"))
        prod = det.find("nfe:prod", namespaces=NS)
        imposto = det.find("nfe:imposto", namespaces=NS)

        itens.append(
            Item(
                numero=numero_item,
                codigo=_text(prod, "nfe:cProd"),
                descricao=_text(prod, "nfe:xProd"),
                cfop=_text(prod, "nfe:CFOP"),
                ncm=_text(prod, "nfe:NCM"),
                unidade=_text(prod, "nfe:uCom"),
                quantidade=to_float(_text(prod, "nfe:qCom")),
                valor_unitario=to_float(_text(prod, "nfe:vUnCom")),
                valor_total=to_float(_text(prod, "nfe:vProd")),
                icms=to_float(_text(imposto, "nfe:ICMS//nfe:vICMS") if imposto is not None else ""),
                ipi=to_float(_text(imposto, "nfe:IPI/nfe:IPITrib/nfe:vIPI") if imposto is not None else ""),
            )
        )

    pagamentos: List[Pagamento] = []
    for det_pag in inf.findall("nfe:pag/nfe:detPag", namespaces=NS):
        pagamentos.append(
            Pagamento(
                forma=_text(det_pag, "nfe:tPag"),
                valor=to_float(_text(det_pag, "nfe:vPag")),
            )
        )

    return NotaFiscal(
        chave=chave,
        numero=numero,
        serie=serie,
        emitente_nome=emitente_nome,
        emitente_cnpj=emitente_cnpj,
        destinatario_nome=destinatario_nome,
        destinatario_doc=destinatario_doc,
        data_emissao=emissao,
        valor_total=valor_total,
        icms_total=icms_total,
        arquivo=xml_path,
        itens=itens,
        pagamentos=pagamentos,
    )
