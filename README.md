# Nifty / BankNifty Signal Assistant

A CrewAI **Flow**-based pipeline that:

1. Fetches Nifty/BankNifty price data (real via Groww API, or dummy data for testing)
2. Computes technical indicators (EMA crossover, RSI, VWAP deviation)
3. Generates a **rule-based** BUY / SELL / HOLD signal — deterministic, no LLM involved
4. Uses an LLM *only* to explain the signal in plain English and flag conflicting indicators

**Important:** This is a decision-support scaffold, not a proven trading system, and nothing
here is financial advice. The rules in `strategy.py` are simple starting points you should
backtest and tune extensively before risking real capital. Options (F&O) trading carries high
risk of loss.

## Project structure

```
nifty_bnf_strategy/
├── .env.example        # copy to .env and fill in
├── requirements.txt
├── config.py            # symbols, thresholds, mode switch
├── data_provider.py     # GrowwDataProvider (real) + DummyDataProvider (fake data)
├── indicators.py         # EMA, RSI, VWAP deviation calculations
├── strategy.py           # rule-based signal logic
└── main_flow.py          # CrewAI Flow tying it all together
```

## Setup

1. `python -m venv venv` then activate it
2. `pip install -r requirements.txt`
3. `cp .env.example .env` and fill in:
   - `OPENAI_API_KEY` (or swap for Anthropic — see `main_flow.py`)
   - `DATA_MODE=dummy` to start (no broker subscription needed)
   - Later, `DATA_MODE=groww` + `GROWW_API_AUTH_TOKEN` once you have a Groww Trading API
     subscription (₹499/month as of late 2025) and have generated a token per Groww's docs:
     https://groww.in/trade-api/docs/python-sdk

## Run

```
python main_flow.py
```

With `DATA_MODE=dummy`, this runs end-to-end immediately with synthetic candle data, so you can
see the full pipeline (data → indicators → signal → LLM explanation) work before connecting
anything real.

## Switching to real Groww data

1. Buy the Groww Trading API subscription in the Groww app (Settings → Trading APIs)
2. Generate a TOTP key + secret (recommended — no daily re-approval needed)
3. `pip install growwapi`
4. Set `DATA_MODE=groww` in `.env` and fill in the Groww auth fields
5. `data_provider.py` already has the `GrowwDataProvider` class stubbed out — you'll fill in
   the auth flow per Groww's current docs (auth flows occasionally change, so check
   https://groww.in/trade-api/docs/python-sdk/authentication for the latest steps)

## Next steps once this works end-to-end

- **Backtest first.** Before trusting any signal, run `strategy.py`'s rules against months of
  historical candles and measure hit rate / drawdown — don't paper-trade or live-trade an
  unbacktested rule set.
- Add option-chain-based signals (OI buildup, PCR) once you're comfortable with the price-based
  rules — Groww's SDK added option chain retrieval in v1.3.0.
- Consider a paper-trading mode before wiring up real order placement.
