# Binance Futures Auto Trader

Ferramenta modular em Python para análise técnica, order flow e execução automática de estratégias no mercado futuro (USDT-M) da Binance.

## Principais recursos
- Carregamento automático de histórico e streaming via websockets (klines, trades, liquidações).
- Núcleo de análise técnica com indicadores clássicos (EMA, RSI, MACD, Bandas de Bollinger) e detecção de breaks de estrutura.
- Monitoramento de order flow, pressão de liquidação e classificação de regime de volatilidade.
- Motor de decisão configurável via pesos (trend, momentum, fluxo e liquidez).
- Gestão de risco com dimensionamento automático (ATR-based), SL/TP/trailing opcionais e controle de alavancagem.
- Execução de ordens (market, stop, take-profit) com gerenciamento de portfólio para múltiplos ativos.

## Requisitos
- Python 3.11+
- Conta Binance com API Key habilitada para Futures (ou conta testnet)

Instale dependências:

```bash
pip install -r requirements.txt
```

## Configuração
1. Copie `config/settings.example.yaml` para `config/settings.yaml`.
2. Informe `api_key` e `api_secret` (use chaves de testnet para modo `paper`).
3. Ajuste parâmetros gerais (saldo, alavancagem, risco por trade, timeframe, etc.).
4. Configure pesos de sinal conforme sua preferência.

## Execução
```bash
python -m app.main BTCUSDT --log-level INFO
```

Argumentos adicionais:
- `--config` : caminho customizado para `settings.yaml`.
- `--once` : roda apenas um ciclo (fechamento de candle) e encerra.

## Avisos importantes
- Utilize primeiro em `paper` (testnet) e valide com backtests dedicados.
- Ajuste limites de risco, tamanhos mínimos e verifique regras da Binance para o par escolhido.
- Monitore logs em `logs/trading.log`.

Este projeto tem caráter educacional. Trading envolve riscos significativos. Utilize por sua conta e risco.
