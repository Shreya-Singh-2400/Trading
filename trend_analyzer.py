import pandas as pd


# ============================================================
# MARKET STRUCTURE
# ============================================================

def detect_market_structure(df: pd.DataFrame) -> dict:
    """
    Detect recent swing highs and swing lows.

    This is intentionally simple for now.
    We will improve swing detection and breakout detection
    after the basic multi-factor engine is stable.
    """

    if len(df) < 10:
        return {
            "structure": "INSUFFICIENT_DATA",
            "support": None,
            "resistance": None,
            "swing_high": None,
            "swing_low": None,
        }

    recent = df.tail(30).copy()

    recent["swing_high"] = (
        (recent["high"] > recent["high"].shift(1))
        & (recent["high"] > recent["high"].shift(-1))
    )

    recent["swing_low"] = (
        (recent["low"] < recent["low"].shift(1))
        & (recent["low"] < recent["low"].shift(-1))
    )

    swing_highs = recent.loc[
        recent["swing_high"], "high"
    ].tolist()

    swing_lows = recent.loc[
        recent["swing_low"], "low"
    ].tolist()

    if swing_lows:
        support = round(
            min(swing_lows[-3:]),
            2
        )
    else:
        support = round(
            recent["low"].min(),
            2
        )

    if swing_highs:
        resistance = round(
            max(swing_highs[-3:]),
            2
        )
    else:
        resistance = round(
            recent["high"].max(),
            2
        )

    # --------------------------------------------------------
    # Determine structure
    # --------------------------------------------------------

    if len(swing_highs) >= 2 and len(swing_lows) >= 2:

        previous_high = swing_highs[-2]
        latest_high = swing_highs[-1]

        previous_low = swing_lows[-2]
        latest_low = swing_lows[-1]

        higher_high = latest_high > previous_high
        higher_low = latest_low > previous_low

        lower_high = latest_high < previous_high
        lower_low = latest_low < previous_low

        if higher_high and higher_low:
            structure = "BULLISH_STRUCTURE"

        elif lower_high and lower_low:
            structure = "BEARISH_STRUCTURE"

        else:
            structure = "MIXED_STRUCTURE"

    else:
        structure = "INSUFFICIENT_SWINGS"

    return {
        "structure": structure,
        "support": support,
        "resistance": resistance,
        "swing_high": (
            round(swing_highs[-1], 2)
            if swing_highs
            else None
        ),
        "swing_low": (
            round(swing_lows[-1], 2)
            if swing_lows
            else None
        ),
    }


# ============================================================
# TREND COMPONENT
# ============================================================

def analyze_trend_component(latest, structure_data):

    score = 0
    evidence = []

    # EMA alignment
    if (
        latest["ema_fast"]
        > latest["ema_slow"]
        > latest["ema_50"]
    ):
        score += 2
        evidence.append(
            "EMA alignment is bullish (9 > 21 > 50)"
        )

    elif (
        latest["ema_fast"]
        < latest["ema_slow"]
        < latest["ema_50"]
    ):
        score -= 2
        evidence.append(
            "EMA alignment is bearish (9 < 21 < 50)"
        )

    else:
        evidence.append(
            "EMA alignment is mixed"
        )

    # Market structure
    structure = structure_data["structure"]

    if structure == "BULLISH_STRUCTURE":
        score += 2
        evidence.append(
            "Market structure shows higher highs and higher lows"
        )

    elif structure == "BEARISH_STRUCTURE":
        score -= 2
        evidence.append(
            "Market structure shows lower highs and lower lows"
        )

    elif structure == "MIXED_STRUCTURE":
        evidence.append(
            "Market structure is mixed"
        )

    return score, evidence


# ============================================================
# MOMENTUM COMPONENT
# ============================================================

def analyze_momentum_component(latest):

    score = 0
    evidence = []
    warnings = []

    # MACD
    if latest["macd"] > latest["macd_signal"]:

        score += 1

        evidence.append(
            "MACD momentum is bullish"
        )

    else:

        score -= 1

        evidence.append(
            "MACD momentum is bearish"
        )

    # RSI
    rsi = latest["rsi"]

    if 55 <= rsi < 70:

        score += 1

        evidence.append(
            "RSI supports bullish momentum"
        )

    elif 30 < rsi <= 45:

        score -= 1

        evidence.append(
            "RSI supports bearish momentum"
        )

    elif rsi >= 70:

        warnings.append(
            "RSI is overbought"
        )

        evidence.append(
            "RSI is overbought; bullish momentum may be extended"
        )

    elif rsi <= 30:

        warnings.append(
            "RSI is oversold"
        )

        evidence.append(
            "RSI is oversold; bearish momentum may be extended"
        )

    else:

        evidence.append(
            "RSI is neutral"
        )

    return score, evidence, warnings


# ============================================================
# POSITION COMPONENT
# ============================================================

def analyze_position_component(latest):

    if latest["close"] > latest["vwap"]:

        return (
            1,
            ["Price is above VWAP"]
        )

    else:

        return (
            -1,
            ["Price is below VWAP"]
        )


# ============================================================
# TREND STRENGTH COMPONENT
# ============================================================

def analyze_strength_component(latest):

    score = 0
    evidence = []

    adx = latest["adx"]

    # ADX measures strength, NOT direction.
    if adx >= 25:

        trend_strength = "STRONG"

        evidence.append(
            "ADX indicates a strong trend"
        )

    elif adx >= 18:

        trend_strength = "MODERATE"

        evidence.append(
            "ADX indicates a developing trend"
        )

    else:

        trend_strength = "WEAK"

        evidence.append(
            "ADX indicates weak trend strength"
        )

    # DI provides direction
    if latest["plus_di"] > latest["minus_di"]:

        score += 1

        evidence.append(
            "+DI is above -DI"
        )

    else:

        score -= 1

        evidence.append(
            "-DI is above +DI"
        )

    return score, trend_strength, evidence


# ============================================================
# BOLLINGER / VOLATILITY
# ============================================================

def analyze_volatility(latest):

    warnings = []
    evidence = []

    bb_position = latest["bb_position"]

    if bb_position >= 0.85:

        warnings.append(
            "Price is near the upper Bollinger Band"
        )

        evidence.append(
            "Price is near the upper Bollinger Band"
        )

    elif bb_position <= 0.15:

        warnings.append(
            "Price is near the lower Bollinger Band"
        )

        evidence.append(
            "Price is near the lower Bollinger Band"
        )

    else:

        evidence.append(
            "Price is inside the Bollinger Band range"
        )

    return evidence, warnings


# ============================================================
# FINAL MARKET ANALYSIS
# ============================================================

def analyze_trend(df: pd.DataFrame) -> dict:
    """
    Multi-factor market analysis.

    IMPORTANT:
    Confidence represents agreement between technical
    evidence. It is NOT the probability of a price move.
    """

    latest = df.iloc[-1]

    # --------------------------------------------------------
    # Structure
    # --------------------------------------------------------

    structure_data = detect_market_structure(df)

    # --------------------------------------------------------
    # Individual components
    # --------------------------------------------------------

    trend_score, trend_evidence = analyze_trend_component(
        latest,
        structure_data
    )

    momentum_score, momentum_evidence, momentum_warnings = (
        analyze_momentum_component(latest)
    )

    position_score, position_evidence = (
        analyze_position_component(latest)
    )

    strength_score, trend_strength, strength_evidence = (
        analyze_strength_component(latest)
    )

    volatility_evidence, volatility_warnings = (
        analyze_volatility(latest)
    )

    # --------------------------------------------------------
    # Component scores
    # --------------------------------------------------------

    component_scores = {
        "trend": trend_score,
        "momentum": momentum_score,
        "position": position_score,
        "strength": strength_score,
    }

    # --------------------------------------------------------
    # Weighted score
    #
    # Trend = 40%
    # Momentum = 25%
    # Position = 15%
    # Strength = 20%
    # --------------------------------------------------------

    weighted_score = (
        trend_score * 0.40
        + momentum_score * 0.25
        + position_score * 0.15
        + strength_score * 0.20
    )

    # --------------------------------------------------------
    # Determine direction
    # --------------------------------------------------------

    if weighted_score >= 1.20:

        bias = "STRONGLY_BULLISH"

    elif weighted_score >= 0.35:

        bias = "BULLISH"

    elif weighted_score <= -1.20:

        bias = "STRONGLY_BEARISH"

    elif weighted_score <= -0.35:

        bias = "BEARISH"

    else:

        bias = "NEUTRAL"

    # --------------------------------------------------------
    # Evidence agreement
    # --------------------------------------------------------

    positive_components = sum(
        score > 0
        for score in component_scores.values()
    )

    negative_components = sum(
        score < 0
        for score in component_scores.values()
    )

    active_components = (
        positive_components
        + negative_components
    )

    if active_components == 0:

        agreement = "LOW"

    else:

        agreement_ratio = max(
            positive_components,
            negative_components
        ) / active_components

        if agreement_ratio >= 0.75:

            agreement = "HIGH"

        elif agreement_ratio >= 0.50:

            agreement = "MODERATE"

        else:

            agreement = "LOW"

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    if (
        agreement == "HIGH"
        and trend_strength == "STRONG"
    ):

        confidence = "HIGH"

    elif (
        agreement in ["HIGH", "MODERATE"]
        and trend_strength in ["STRONG", "MODERATE"]
    ):

        confidence = "MODERATE-HIGH"

    elif agreement == "MODERATE":

        confidence = "MODERATE"

    else:

        confidence = "LOW"

    # --------------------------------------------------------
    # Combine evidence
    # --------------------------------------------------------

    evidence = (
        trend_evidence
        + momentum_evidence
        + position_evidence
        + strength_evidence
        + volatility_evidence
    )

    warnings = (
        momentum_warnings
        + volatility_warnings
    )

    # Remove duplicate warnings
    warnings = list(dict.fromkeys(warnings))

    # --------------------------------------------------------
    # Return structured analysis
    # --------------------------------------------------------

    return {

        "bias": bias,

        "confidence": confidence,

        "trend_strength": trend_strength,

        "weighted_score": round(
            weighted_score,
            3
        ),

        "trend_score": trend_score,

        "momentum_score": momentum_score,

        "position_score": position_score,

        "strength_score": strength_score,

        "close": round(
            latest["close"],
            2
        ),

        "rsi": round(
            latest["rsi"],
            2
        ),

        "adx": round(
            latest["adx"],
            2
        ),

        "atr": round(
            latest["atr"],
            2
        ),

        "vwap": round(
            latest["vwap"],
            2
        ),

        "macd": round(
            latest["macd"],
            2
        ),

        "macd_signal": round(
            latest["macd_signal"],
            2
        ),

        "bb_position": round(
            latest["bb_position"],
            3
        ),

        "support": structure_data["support"],

        "resistance": structure_data["resistance"],

        "swing_high": structure_data["swing_high"],

        "swing_low": structure_data["swing_low"],

        "structure": structure_data["structure"],

        "evidence": evidence,

        "warnings": warnings,
    }