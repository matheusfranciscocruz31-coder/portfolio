# XML para Excel (NF-e)

Conversor em Python que transforma notas fiscais eletronicas (NF-e) em planilhas Excel organizadas, prontas para auditoria e integracao em ERPs.

## Recursos

- Leitura de XML individuais ou pastas inteiras (inclui arquivos `.zip`).
- Extracao de dados chave: emitente, destinatario, impostos, totais e itens.
- Geracao de planilha com abas:
  - **Resumo**: cabecalho da nota, valores e impostos.
  - **Itens**: produtos com CFOP, NCM, quantidade, valores e tributos.
  - **Pagamentos**: formas de pagamento (PIX, cartao, boleto etc).
- Normalizacao opcional de chaves, CNPJ/CPF e datas.
- Validacao rapida para identificar XMLs corrompidos ou com schema divergente.

## Estrutura

```
projetos/xml-para-excel
├── xml_para_excel
│   ├── __init__.py
│   ├── converter.py
│   ├── parser.py
│   └── utils.py
├── cli.py
├── requirements.txt
├── samples
│   └── nfe_exemplo.xml
└── output
```

## Instalacao

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

```bash
python cli.py --input samples --output output
```

Argumentos principais:

| Flag | Descricao |
|------|-----------|
| `--input` | Arquivo XML unico ou diretorio com multiplos XMLs (ou `.zip`). |
| `--output` | Pasta onde o Excel sera salvo. |
| `--arquivo` | Nome base do arquivo Excel (opcional, padrao: `notas.xlsx`). |
| `--normalizar` | Habilita limpeza de CNPJ/CPF, chaves e datas. |
| `--dry-run` | Apenas valida os XMLs, sem gerar planilha. |

Saida padrao:

- `notas.xlsx` com abas Resumo, Itens e Pagamentos
- `processamento.log` com eventuais alertas

## Exemplos

Gerar Excel agrupando varias notas:

```bash
python cli.py --input C:\NFCE\lote --output output --arquivo consolidado.xlsx
```

Validar apenas a leitura (sem gerar planilha):

```bash
python cli.py --input samples --output output --dry-run
```

## Automacao

- Compativel com agendamento via Task Scheduler;
- Para uso em ETLs, importe `xml_para_excel.converter.build_workbook` diretamente;
- Exporta DataFrames (`pandas`) intermediarios, facilitando integracoes com SQL.

## Licenca

MIT. Utilize como base para projetos internos de auditoria ou integracao contabil.
