# Dashboard Financeiro Automatizado

Aplicacao em Streamlit para consolidar indicadores diarios de fluxo de caixa, receitas, despesas e previsoes usando fontes heterogeneas (CSV, Excel ou Google Sheets).

## O que o projeto entrega

- ETL leve que padroniza e junta arquivos de receitas, despesas e projecoes.
- Atualizacao automatica (cron + API Sheets opcional) com persistencia em SQLite.
- Dashboard interativo com graficos de fluxo cumulativo, margem e composicao por centro de custo.
- Exportacao de relatorio instantaneo em PDF.

## Estrutura

```
projetos/dashboard-financeiro
├── dashboard_financeiro
│   ├── __init__.py
│   ├── data_loader.py
│   ├── metrics.py
│   ├── persistence.py
│   └── ui.py
├── app.py            # entrypoint Streamlit
├── data
│   ├── despesas.csv
│   ├── receitas.csv
│   └── previsoes.csv
├── settings.example.toml
├── requirements.txt
└── README.md
```

## Pré-requisitos

- Python 3.11+
- Pacotes listados em `requirements.txt`
- Conta Streamlit Cloud (opcional) para deploy 1-clique.

Instale dependencias:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Como rodar

1. Duplique `settings.example.toml` para `settings.toml` e ajuste caminhos/IDs desejados.
2. Execute a sincronizacao local (opcional):

```bash
python -m dashboard_financeiro.data_loader sync --config settings.toml
```

3. Inicie o dashboard:

```bash
streamlit run app.py --server.port 8501
```

## Principais telas

- **Visão Geral**: saldo inicial, entradas/saidas do periodo, fluxo projetado nos proximos 30 dias.
- **Centros de custo**: barras empilhadas com comparativo real x previsto.
- **Clientes/Fornecedores**: ranking com aging automatizado.
- **Análise diária**: grafico de linha com saldo acumulado e destaques de desvios.

## Automatização

- Script de sincronização consulta planilhas (Google Sheets) ou arquivos dropados em `data/`.
- Processamento salva dados normalizados em SQLite (`finance.db`) com carimbo de atualização.
- Dashboard conecta no banco e gera indicadores em tempo real.
- Comando extra `python app.py --export pdf` gera snapshot do painel principal.

## Deploy

1. Faça push para GitHub.
2. No Streamlit Cloud, conecte o repo e configure secret `CONFIG_FILE=settings.toml` se usar Sheets.
3. Agende a sincronização com GitHub Actions ou Windows Task Scheduler chamando `python -m dashboard_financeiro.data_loader sync`.

## Licenca

MIT. Use como base para dashboards financeiros internos.
