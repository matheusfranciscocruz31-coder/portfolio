# Automacao de Relatorios

Pipeline em Python para normalizar dados de vendas, gerar relatórios executivos (Excel + PDF) e preparar um resumo de envio por e-mail.

## Visao geral

- Importa arquivos CSV ou XLSX com vendas brutas.
- Valida colunas obrigatorias, tipos e valores inconsistentes.
- Gera planilha consolidada com abas de indicadores, totais por cliente, produto e periodo.
- Exporta relatorio em PDF (via tabela HTML renderizada pelo Pandas) e arquivo `.eml` pronto para disparo.
- Permite agendar o processamento para rodadas diarias, semanais ou mensais.

## Estrutura

```
projetos/automacao-relatorios
├── automacao_relatorios
│   ├── __init__.py
│   ├── email_utils.py
│   ├── report_generator.py
│   └── validation.py
├── cli.py
├── data
│   └── vendas_exemplo.csv
├── output
│   └── (arquivos gerados)
└── requirements.txt
```

## Requisitos rapidos

- Python 3.11 ou superior.
- Dependencias listadas em `requirements.txt`.

Instale com:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Como usar

1. Ajuste o dataset de entrada (`data/`) ou avalie com o arquivo de exemplo.
2. Execute a CLI apontando a pasta de origem:

```bash
python cli.py --input data --output output --formato excel pdf \
  --janela mensal --smtp-config smtp_config.json
```

Argumentos principais:

| Flag | Descricao |
|------|-----------|
| `--input` | Diretorio com arquivos CSV/XLSX. |
| `--output` | Diretorio final (criado automaticamente). |
| `--formato` | Formatos desejados: `excel`, `pdf`, `email`. Aceita varios. |
| `--janela` | `diaria`, `semanal` ou `mensal` para ajustar filtros de data. |
| `--smtp-config` | Caminho para JSON com credenciais SMTP (opcional). |

O PDF e o e-mail sao gerados quando o `wkhtmltopdf` nao esta disponivel? Nada. Usamos somente recursos nativos do Pandas + `DataFrame.to_html`. O arquivo `.eml` fica dentro do `output`.

## Agendamento

Para execucao automatica no Windows Task Scheduler, utilize um `.bat` com:

```
@echo off
call C:\caminho\para\projetos\automacao-relatorios\.venv\Scripts\activate
python C:\caminho\para\projetos\automacao-relatorios\cli.py --input ... --output ...
```

## Testes rapidos

```bash
python cli.py --input data --output output --formato excel email
```

O script criara:

- `relatorio_resumo.xlsx`
- `relatorio_resumo.pdf`
- `resumo_email.eml`

## Observacoes

- Os alertas e logs ficam no console e, quando `--formato email` for usado, sao replicados no corpo do e-mail.
- O PDF depende da biblioteca `pdfkit`; caso nao esteja disponivel, um aviso aparece e somente o Excel e o e-mail sao emitidos.
