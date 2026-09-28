"""
Data providers for NIFTY / BANKNIFTY market analysis.

DummyDataProvider:
    Generates one underlying synthetic market path and
    aggregates it into multiple timeframes.

GrowwDataProvider:
    Fetches real historical candles from Groww.
"""

import time
import numpy as np
import pandas as pd

import config


# ============================================================
# DUMMY DATA PROVIDER
# ============================================================

class DummyDataProvider:
    """
    Generates synthetic market data.

    IMPORTANT:
    This is ONLY for testing the software architecture.

    It must NOT be used to evaluate whether a trading
    strategy is profitable.
    """

    def __init__(self):

        # Fixed seeds make the synthetic market reproducible.
        self.seeds = {
            "NIFTY": 12345,
            "BANKNIFTY": 67890,
        }

        self.base_prices = {
            "NIFTY": 24000,
            "BANKNIFTY": 51000,
        }

        # Cache the underlying 1-minute market.
        self._base_data = {}

    # --------------------------------------------------------
    # Generate underlying 1-minute data
    # --------------------------------------------------------

    def _generate_base_data(self, symbol_key):

        if symbol_key in self._base_data:
            return self._base_data[symbol_key].copy()

        rng = np.random.default_rng(
            self.seeds[symbol_key]
        )

        # Enough 1-minute candles for:
        #
        # 5m  → 300 candles
        # 15m → 200 candles
        # 1h  → 120 candles
        #
        # 120 hours × 60 minutes = 7200 candles
        #

        n = 7200

        base_price = self.base_prices[
            symbol_key
        ]

        # Small 1-minute movements.
        returns = rng.normal(
            loc=0.0,
            scale=0.00035,
            size=n
        )

        closes = (
            base_price
            * np.cumprod(
                1 + returns
            )
        )

        # Generate realistic-ish OHLC around close.
        highs = closes * (
            1
            + rng.uniform(
                0.0001,
                0.0006,
                size=n
            )
        )

        lows = closes * (
            1
            - rng.uniform(
                0.0001,
                0.0006,
                size=n
            )
        )

        opens = np.empty(n)

        opens[0] = base_price

        opens[1:] = closes[:-1]

        volumes = rng.integers(
            5_000,
            50_000,
            size=n
        )

        timestamps = pd.date_range(
            end=pd.Timestamp.now(),
            periods=n,
            freq="1min"
        )

        df = pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes,
            }
        )

        self._base_data[symbol_key] = df

        return df.copy()

    # --------------------------------------------------------
    # Aggregate 1-minute data into timeframe
    # --------------------------------------------------------

    def get_candles(
        self,
        symbol_key: str,
        interval_minutes: int = None
    ) -> pd.DataFrame:

        if interval_minutes is None:
            interval_minutes = (
                config.CANDLE_INTERVAL_MINUTES
            )

        base = self._generate_base_data(
            symbol_key
        )

        df = base.copy()

        df["timestamp"] = pd.to_datetime(
            df["timestamp"]
        )

        df = df.set_index("timestamp")

        rule = f"{interval_minutes}min"

        aggregated = df.resample(rule).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )

        aggregated = aggregated.dropna()

        if interval_minutes == 5:
            aggregated = aggregated.tail(300)

        elif interval_minutes == 15:
            aggregated = aggregated.tail(200)

        elif interval_minutes == 60:
            aggregated = aggregated.tail(120)

        else:
            aggregated = aggregated.tail(200)

        return aggregated.reset_index()

    # --------------------------------------------------------
    # Get historical candles up to a specific timestamp
    # --------------------------------------------------------

    def get_candles_asof(
        self,
        symbol_key: str,
        interval_minutes: int = None,
        end_time=None
    ) -> pd.DataFrame:

        if interval_minutes is None:
            interval_minutes = (
                config.CANDLE_INTERVAL_MINUTES
            )

        if end_time is None:
            raise ValueError(
                "end_time is required for get_candles_asof()"
            )

        base = self._generate_base_data(
            symbol_key
        )

        df = base.copy()

        df["timestamp"] = pd.to_datetime(
            df["timestamp"]
        )

        end_time = pd.Timestamp(end_time)

        df = df[
            df["timestamp"] < end_time
        ]

        if df.empty:
            return pd.DataFrame()

        df = df.set_index("timestamp")

        rule = f"{interval_minutes}min"

        aggregated = df.resample(rule).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )

        aggregated = aggregated.dropna()

        if interval_minutes == 5:
            limit = 300

        elif interval_minutes == 15:
            limit = 200

        elif interval_minutes == 60:
            limit = 120

        else:
            limit = 200

        aggregated = aggregated.tail(limit)

        return (
            aggregated
            .reset_index()
            .reset_index(drop=True)
        )
# ============================================================
# GROWW DATA PROVIDER
# ============================================================

class GrowwDataProvider:
    """
    Real market-data provider using Groww.

    Requires a Groww Trading API subscription with
    market-data access.
    """

    def __init__(self):

        from growwapi import GrowwAPI

        import os

        auth_token = os.getenv(
            "GROWW_ACCESS_TOKEN"
        )

        if not auth_token:

            raise RuntimeError(
                "GROWW_API_AUTH_TOKEN not set."
            )

        self.client = GrowwAPI(
            auth_token
        )

    def get_candles(
        self,
        symbol_key: str,
        interval_minutes: int = None
    ) -> pd.DataFrame:

        import time as _time

        if interval_minutes is None:

            interval_minutes = (
                config.CANDLE_INTERVAL_MINUTES
            )

        sym = config.SYMBOLS[
            symbol_key
        ]

        end_ms = int(
            _time.time() * 1000
        )

        start_ms = (
            end_ms
            - config.LOOKBACK_HOURS
            * 60
            * 60
            * 1000
        )

        response = self.client.get_historical_candles(
            exchange=self.client.EXCHANGE_NSE,
            segment=self.client.SEGMENT_CASH,
            groww_symbol=f"NSE-{sym['trading_symbol']}",
            start_time=start_ms,
            end_time=end_ms,
            candle_interval=self.client.CANDLE_INTERVAL_MIN_5,
        )
        print("Response type:", type(response))
        print("Response:", response)
        print("Symbol:", f"NSE-{sym['trading_symbol']}")
        print("Start:", start_ms)
        print("End:", end_ms)
        print("Interval:", self.client.CANDLE_INTERVAL_MIN_5)
        
        candles = response["candles"]

        return pd.DataFrame(
            candles,
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        )


# ============================================================
# PROVIDER FACTORY
# ============================================================

def get_provider():

    if config.DATA_MODE == "groww":

        return GrowwDataProvider()

    return DummyDataProvider()