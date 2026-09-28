"""
Central place for symbols and strategy thresholds.
Tune these once you start backtesting -- don't treat these defaults as "the strategy",
they're just reasonable starting points for a classic EMA/RSI/VWAP setup.
"""

import os
from dotenv import load_dotenv

load_dotenv()

DATA_MODE = os.getenv("DATA_MODE", "dummy")  # "dummy" or "groww"

SYMBOLS = {
    "NIFTY": {"exchange": "NSE", "segment": "CASH", "trading_symbol": "NIFTY"},
    "BANKNIFTY": {"exchange": "NSE", "segment": "CASH", "trading_symbol": "BANKNIFTY"},
}

# Indicator settings
EMA_FAST = 9
EMA_SLOW = 21
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
VWAP_DEVIATION_PCT_THRESHOLD = 0.3  # % distance from VWAP considered "stretched"

# Candle fetch settings
CANDLE_INTERVAL_MINUTES = 5
LOOKBACK_HOURS = 6

LLM_MODEL = "gpt-4o-mini"
