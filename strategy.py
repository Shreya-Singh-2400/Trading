"""
Deterministic, rule-based signal generation.

This is intentionally simple and fully transparent -- every decision can be traced back
to a specific rule. Treat this as a starting skeleton: backtest it, adjust thresholds,
and add/remove rules based on what actually holds up historically before using it live.

No LLM involvement here on purpose -- the decision logic should be inspectable and
repeatable, not dependent on model sampling.
"""

import config


def generate_signal(df) -> dict:
    """Takes an indicator-enriched DataFrame and returns a signal dict for the latest candle."""
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    reasons = []
    score = 0  # positive = bullish, negative = bearish

    # Rule 1: EMA crossover
    ema_bullish_cross = prev["ema_fast"] <= prev["ema_slow"] and latest["ema_fast"] > latest["ema_slow"]
    ema_bearish_cross = prev["ema_fast"] >= prev["ema_slow"] and latest["ema_fast"] < latest["ema_slow"]
    if ema_bullish_cross:
        score += 2
        reasons.append(f"EMA{config.EMA_FAST} crossed above EMA{config.EMA_SLOW} (bullish crossover)")
    elif ema_bearish_cross:
        score -= 2
        reasons.append(f"EMA{config.EMA_FAST} crossed below EMA{config.EMA_SLOW} (bearish crossover)")
    elif latest["ema_fast"] > latest["ema_slow"]:
        score += 1
        reasons.append("Short-term trend above long-term trend (mild bullish bias)")
    else:
        score -= 1
        reasons.append("Short-term trend below long-term trend (mild bearish bias)")

    # Rule 2: RSI
    if latest["rsi"] >= config.RSI_OVERBOUGHT:
        score -= 1
        reasons.append(f"RSI {latest['rsi']:.1f} is overbought (>{config.RSI_OVERBOUGHT})")
    elif latest["rsi"] <= config.RSI_OVERSOLD:
        score += 1
        reasons.append(f"RSI {latest['rsi']:.1f} is oversold (<{config.RSI_OVERSOLD})")

    # Rule 3: VWAP deviation (mean-reversion signal)
    dev = latest["vwap_dev_pct"]
    if dev > config.VWAP_DEVIATION_PCT_THRESHOLD:
        score -= 1
        reasons.append(f"Price is {dev:.2f}% above VWAP (stretched, possible pullback)")
    elif dev < -config.VWAP_DEVIATION_PCT_THRESHOLD:
        score += 1
        reasons.append(f"Price is {dev:.2f}% below VWAP (stretched, possible bounce)")

    if score >= 2:
        signal = "BUY"
    elif score <= -2:
        signal = "SELL"
    else:
        signal = "HOLD"

    return {
        "signal": signal,
        "score": score,
        "reasons": reasons,
        "close": round(float(latest["close"]), 2),
        "rsi": round(float(latest["rsi"]), 2),
        "vwap_dev_pct": round(float(dev), 3),
    }
