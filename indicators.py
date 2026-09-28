"""Technical indicator calculations on a candle DataFrame."""

import numpy as np
import pandas as pd

import config


def add_ema(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["ema_fast"] = df["close"].ewm(
        span=config.EMA_FAST,
        adjust=False
    ).mean()

    df["ema_slow"] = df["close"].ewm(
        span=config.EMA_SLOW,
        adjust=False
    ).mean()

    df["ema_50"] = df["close"].ewm(
        span=50,
        adjust=False
    ).mean()

    return df


def add_rsi(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / config.RSI_PERIOD,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / config.RSI_PERIOD,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    df["rsi"] = 100 - (100 / (1 + rs))
    df["rsi"] = df["rsi"].fillna(50)

    return df


def add_macd(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    ema_12 = df["close"].ewm(
        span=12,
        adjust=False
    ).mean()

    ema_26 = df["close"].ewm(
        span=26,
        adjust=False
    ).mean()

    df["macd"] = ema_12 - ema_26

    df["macd_signal"] = df["macd"].ewm(
        span=9,
        adjust=False
    ).mean()

    df["macd_histogram"] = (
        df["macd"] - df["macd_signal"]
    )

    return df


def add_atr(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    previous_close = df["close"].shift(1)

    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    df["atr"] = true_range.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    return df


def add_adx(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    high_diff = df["high"].diff()
    low_diff = -df["low"].diff()

    plus_dm = np.where(
        (high_diff > low_diff) & (high_diff > 0),
        high_diff,
        0
    )

    minus_dm = np.where(
        (low_diff > high_diff) & (low_diff > 0),
        low_diff,
        0
    )

    previous_close = df["close"].shift(1)

    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    atr = tr.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    plus_di = (
        100
        * pd.Series(plus_dm, index=df.index).ewm(
            alpha=1 / 14,
            adjust=False
        ).mean()
        / atr
    )

    minus_di = (
        100
        * pd.Series(minus_dm, index=df.index).ewm(
            alpha=1 / 14,
            adjust=False
        ).mean()
        / atr
    )

    dx = (
        100
        * (plus_di - minus_di).abs()
        / (plus_di + minus_di).replace(0, np.nan)
    )

    df["plus_di"] = plus_di
    df["minus_di"] = minus_di

    df["adx"] = dx.ewm(
        alpha=1 / 14,
        adjust=False
    ).mean()

    return df


def add_bollinger_bands(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    middle = df["close"].rolling(20).mean()
    std = df["close"].rolling(20).std()

    df["bb_middle"] = middle
    df["bb_upper"] = middle + (2 * std)
    df["bb_lower"] = middle - (2 * std)

    band_width = df["bb_upper"] - df["bb_lower"]

    df["bb_position"] = (
        (df["close"] - df["bb_lower"])
        / band_width.replace(0, np.nan)
    )

    return df


def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    typical_price = (
        df["high"] + df["low"] + df["close"]
    ) / 3

    cum_vol = df["volume"].cumsum()

    cum_vol_price = (
        typical_price * df["volume"]
    ).cumsum()

    df["vwap"] = cum_vol_price / cum_vol

    df["vwap_dev_pct"] = (
        (df["close"] - df["vwap"])
        / df["vwap"]
        * 100
    )

    return df


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators."""

    df = add_ema(df)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_atr(df)
    df = add_adx(df)
    df = add_bollinger_bands(df)
    df = add_vwap(df)

    return df