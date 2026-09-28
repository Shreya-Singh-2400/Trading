"""
Multi-Timeframe Market Analyzer V2

Combines 5m, 15m and 1h analysis into a structured market view.

Timeframe roles:
    1h  -> Higher-timeframe / macro direction
    15m -> Confirmation
    5m  -> Short-term timing

This module does NOT place trades.
It produces market intelligence and identifies
agreement/conflict between timeframes.
"""

from typing import Dict, Any


# Higher timeframes get more influence.
TIMEFRAME_WEIGHTS = {
    "1h": 0.45,
    "15m": 0.35,
    "5m": 0.20,
}


BIAS_SCORES = {
    "STRONGLY_BULLISH": 2.0,
    "BULLISH": 1.0,
    "NEUTRAL": 0.0,
    "BEARISH": -1.0,
    "STRONGLY_BEARISH": -2.0,
}


def _normalise_bias(bias: str) -> str:
    """Return a valid bias value."""

    if not bias:
        return "NEUTRAL"

    bias = str(bias).upper().strip()

    if bias in BIAS_SCORES:
        return bias

    return "NEUTRAL"


def _is_bullish(bias: str) -> bool:
    return _normalise_bias(bias) in [
        "BULLISH",
        "STRONGLY_BULLISH",
    ]


def _is_bearish(bias: str) -> bool:
    return _normalise_bias(bias) in [
        "BEARISH",
        "STRONGLY_BEARISH",
    ]


def calculate_weighted_score(
    timeframe_analysis: Dict[str, Dict[str, Any]]
) -> float:
    """
    Calculate the directional score.

    1h = 45%
    15m = 35%
    5m = 20%
    """

    total = 0.0

    for timeframe, weight in TIMEFRAME_WEIGHTS.items():

        analysis = timeframe_analysis.get(timeframe)

        if not analysis:
            continue

        bias = _normalise_bias(
            analysis.get("bias", "NEUTRAL")
        )

        total += BIAS_SCORES[bias] * weight

    return round(total, 2)


def determine_overall_bias(weighted_score: float) -> str:
    """Convert weighted score into overall directional bias."""

    if weighted_score >= 1.35:
        return "STRONGLY_BULLISH"

    if weighted_score >= 0.35:
        return "BULLISH"

    if weighted_score <= -1.35:
        return "STRONGLY_BEARISH"

    if weighted_score <= -0.35:
        return "BEARISH"

    return "NEUTRAL"


def calculate_directional_agreement(
    timeframe_analysis: Dict[str, Dict[str, Any]]
) -> str:
    """
    Determine whether the timeframe directions agree.
    """

    biases = []

    for timeframe in ["1h", "15m", "5m"]:

        analysis = timeframe_analysis.get(timeframe)

        if analysis:
            biases.append(
                _normalise_bias(
                    analysis.get("bias", "NEUTRAL")
                )
            )

    if len(biases) < 2:
        return "INSUFFICIENT_DATA"

    bullish = sum(_is_bullish(b) for b in biases)
    bearish = sum(_is_bearish(b) for b in biases)
    neutral = sum(b == "NEUTRAL" for b in biases)

    if bullish == len(biases):
        return "FULL_BULLISH_AGREEMENT"

    if bearish == len(biases):
        return "FULL_BEARISH_AGREEMENT"

    if bullish >= 2 and bearish == 0:
        return "BULLISH_WITH_NEUTRAL_CONFIRMATION"

    if bearish >= 2 and bullish == 0:
        return "BEARISH_WITH_NEUTRAL_CONFIRMATION"

    if bullish > 0 and bearish > 0:
        return "TIMEFRAME_CONFLICT"

    if neutral == len(biases):
        return "FULL_NEUTRAL"

    return "MIXED"


def calculate_structure_agreement(
    timeframe_analysis: Dict[str, Dict[str, Any]]
) -> str:
    """
    Evaluate market-structure agreement independently
    from directional bias.

    MIXED = uncertainty without a direct opposite signal.
    CONFLICT = actual bullish-vs-bearish disagreement.
    """

    structures = []

    for timeframe in ["1h", "15m", "5m"]:

        analysis = timeframe_analysis.get(timeframe)

        if not analysis:
            continue

        structure = str(
            analysis.get("structure", "")
        ).upper()

        if "BULLISH" in structure:
            structures.append("BULLISH")

        elif "BEARISH" in structure:
            structures.append("BEARISH")

        elif "MIXED" in structure:
            structures.append("MIXED")

    if len(structures) < 2:
        return "INSUFFICIENT_DATA"

    bullish = structures.count("BULLISH")
    bearish = structures.count("BEARISH")
    mixed = structures.count("MIXED")

    # All structures agree
    if bullish == len(structures):
        return "FULL_BULLISH_STRUCTURE"

    if bearish == len(structures):
        return "FULL_BEARISH_STRUCTURE"

    # Direct bullish-vs-bearish disagreement
    if bullish > 0 and bearish > 0:
        return "STRUCTURE_CONFLICT"

    # No direct opposition; just uncertainty
    if mixed > 0 and bullish > 0:
        return "MOSTLY_BULLISH_STRUCTURE"

    if mixed > 0 and bearish > 0:
        return "MOSTLY_BEARISH_STRUCTURE"

    if mixed == len(structures):
        return "MIXED_STRUCTURE"

    return "MIXED_STRUCTURE"
 
def calculate_momentum_agreement(
    timeframe_analysis: Dict[str, Dict[str, Any]]
) -> str:
    """
    Compare MACD momentum and RSI across timeframes.
    """

    bullish_count = 0
    bearish_count = 0
    neutral_count = 0

    for analysis in timeframe_analysis.values():

        macd = analysis.get("macd")
        signal = analysis.get("macd_signal")
        rsi = analysis.get("rsi")

        if (
            isinstance(macd, (int, float))
            and isinstance(signal, (int, float))
        ):

            macd_bullish = macd > signal
            macd_bearish = macd < signal

        else:
            macd_bullish = False
            macd_bearish = False

        rsi_bullish = (
            isinstance(rsi, (int, float))
            and rsi > 50
        )

        rsi_bearish = (
            isinstance(rsi, (int, float))
            and rsi < 50
        )

        if macd_bullish and rsi_bullish:
            bullish_count += 1

        elif macd_bearish and rsi_bearish:
            bearish_count += 1

        else:
            neutral_count += 1

    if bullish_count == 3:
        return "FULL_BULLISH_MOMENTUM"

    if bearish_count == 3:
        return "FULL_BEARISH_MOMENTUM"

    if bullish_count > bearish_count:
        return "MOSTLY_BULLISH_MOMENTUM"

    if bearish_count > bullish_count:
        return "MOSTLY_BEARISH_MOMENTUM"

    if neutral_count == 3:
        return "NEUTRAL_MOMENTUM"

    return "MIXED_MOMENTUM"


def calculate_trend_strength(
    timeframe_analysis: Dict[str, Dict[str, Any]]
) -> str:
    """
    Calculate trend strength using a weighted ADX.

    Unlike V1, the 1h ADX receives the largest weight.
    """

    weighted_adx = 0.0
    total_weight = 0.0

    for timeframe, weight in TIMEFRAME_WEIGHTS.items():

        analysis = timeframe_analysis.get(timeframe)

        if not analysis:
            continue

        adx = analysis.get("adx")

        if isinstance(adx, (int, float)):

            weighted_adx += float(adx) * weight
            total_weight += weight

    if total_weight == 0:
        return "UNKNOWN"

    weighted_adx /= total_weight

    if weighted_adx >= 25:
        return "STRONG"

    if weighted_adx >= 18:
        return "MODERATE"

    return "WEAK"


def determine_higher_timeframe_confirmation(
    timeframe_analysis: Dict[str, Dict[str, Any]]
) -> str:
    """
    Determine whether 15m and 5m confirm the 1h direction.
    """

    one_hour = timeframe_analysis.get("1h")
    fifteen = timeframe_analysis.get("15m")
    five = timeframe_analysis.get("5m")

    if not one_hour or not fifteen or not five:
        return "INSUFFICIENT_DATA"

    higher_bias = _normalise_bias(
        one_hour.get("bias")
    )

    middle_bias = _normalise_bias(
        fifteen.get("bias")
    )

    lower_bias = _normalise_bias(
        five.get("bias")
    )

    # -----------------------------------------
    # Higher timeframe is bullish
    # -----------------------------------------

    if _is_bullish(higher_bias):

        if _is_bullish(middle_bias) and _is_bullish(lower_bias):
            return "FULL_BULLISH_CONFIRMATION"

        if _is_bullish(middle_bias) or _is_bullish(lower_bias):
            return "PARTIAL_BULLISH_CONFIRMATION"

        return "BULLISH_HIGHER_TF_UNCONFIRMED"

    # -----------------------------------------
    # Higher timeframe is bearish
    # -----------------------------------------

    if _is_bearish(higher_bias):

        if _is_bearish(middle_bias) and _is_bearish(lower_bias):
            return "FULL_BEARISH_CONFIRMATION"

        if _is_bearish(middle_bias) or _is_bearish(lower_bias):
            return "PARTIAL_BEARISH_CONFIRMATION"

        return "BEARISH_HIGHER_TF_UNCONFIRMED"

    # -----------------------------------------
    # Higher timeframe is neutral
    # -----------------------------------------

    if _is_bullish(middle_bias) and _is_bullish(lower_bias):
        return "LOWER_TF_BULLISH_EMERGENCE"

    if _is_bearish(middle_bias) and _is_bearish(lower_bias):
        return "LOWER_TF_BEARISH_EMERGENCE"

    return "NO_CLEAR_HIGHER_TF_CONFIRMATION"


def determine_market_state(
    overall_bias: str,
    confirmation: str,
    trend_strength: str,
    structure_agreement: str,
    momentum_agreement: str,
) -> str:
    """
    Produce a conservative market state.

    Direction alone is not enough.
    Structure + momentum + confirmation are considered.
    """

    bullish_confirmation = confirmation in [
        "FULL_BULLISH_CONFIRMATION",
        "PARTIAL_BULLISH_CONFIRMATION",
    ]

    bearish_confirmation = confirmation in [
        "FULL_BEARISH_CONFIRMATION",
        "PARTIAL_BEARISH_CONFIRMATION",
    ]

    bullish_structure = structure_agreement in [
        "FULL_BULLISH_STRUCTURE",
        "MOSTLY_BULLISH_STRUCTURE",
    ]

    bearish_structure = structure_agreement in [
        "FULL_BEARISH_STRUCTURE",
        "MOSTLY_BEARISH_STRUCTURE",
    ]

    bullish_momentum = momentum_agreement in [
        "FULL_BULLISH_MOMENTUM",
        "MOSTLY_BULLISH_MOMENTUM",
    ]

    bearish_momentum = momentum_agreement in [
        "FULL_BEARISH_MOMENTUM",
        "MOSTLY_BEARISH_MOMENTUM",
    ]

    # Strong bullish environment
    if (
        overall_bias == "STRONGLY_BULLISH"
        and trend_strength == "STRONG"
        and bullish_confirmation
        and bullish_structure
        and bullish_momentum
    ):
        return "STRONG_BULLISH_ENVIRONMENT"

    # Strong bearish environment
    if (
        overall_bias == "STRONGLY_BEARISH"
        and trend_strength == "STRONG"
        and bearish_confirmation
        and bearish_structure
        and bearish_momentum
    ):
        return "STRONG_BEARISH_ENVIRONMENT"

    # Bullish
    if overall_bias in [
        "BULLISH",
        "STRONGLY_BULLISH",
    ]:

        if (
            bullish_confirmation
            and bullish_structure
            and bullish_momentum
        ):
            return "BULLISH_WITH_CONFIRMATION"

        return "CAUTIOUS_BULLISH"

    # Bearish
    if overall_bias in [
        "BEARISH",
        "STRONGLY_BEARISH",
    ]:

        if (
            bearish_confirmation
            and bearish_structure
            and bearish_momentum
        ):
            return "BEARISH_WITH_CONFIRMATION"

        return "CAUTIOUS_BEARISH"

    # Neutral but lower TFs are moving
    if confirmation == "LOWER_TF_BULLISH_EMERGENCE":
        return "EARLY_BULLISH_EMERGENCE"

    if confirmation == "LOWER_TF_BEARISH_EMERGENCE":
        return "EARLY_BEARISH_EMERGENCE"

    return "NEUTRAL / RANGE-LIKE"


def generate_evidence(
    timeframe_analysis: Dict[str, Dict[str, Any]],
    agreement: str,
    confirmation: str,
    structure_agreement: str,
    momentum_agreement: str,
) -> list:
    """
    Generate detailed, explainable evidence.
    """

    evidence = []

    # -----------------------------------------
    # Individual timeframe summaries
    # -----------------------------------------

    for timeframe in ["1h", "15m", "5m"]:

        analysis = timeframe_analysis.get(timeframe)

        if not analysis:
            continue

        bias = _normalise_bias(
            analysis.get("bias")
        )

        structure = analysis.get(
            "structure",
            "UNKNOWN"
        )

        strength = analysis.get(
            "trend_strength",
            "UNKNOWN"
        )

        rsi = analysis.get("rsi")
        adx = analysis.get("adx")

        evidence.append(
            f"{timeframe}: {bias} bias, "
            f"{structure}, "
            f"{strength} trend."
        )

        # RSI
        if isinstance(rsi, (int, float)):

            if rsi >= 70:
                evidence.append(
                    f"{timeframe}: RSI {rsi:.2f} "
                    f"indicates overbought conditions."
                )

            elif rsi <= 30:
                evidence.append(
                    f"{timeframe}: RSI {rsi:.2f} "
                    f"indicates oversold conditions."
                )

        # ADX
        if isinstance(adx, (int, float)):

            if adx >= 25:
                evidence.append(
                    f"{timeframe}: ADX {adx:.2f} "
                    f"indicates a relatively strong trend."
                )

            elif adx < 18:
                evidence.append(
                    f"{timeframe}: ADX {adx:.2f} "
                    f"indicates weak trend strength."
                )

    # -----------------------------------------
    # Cross-timeframe evidence
    # -----------------------------------------

    evidence.append(
        f"Directional agreement: {agreement}."
    )

    evidence.append(
        f"Higher-timeframe confirmation: {confirmation}."
    )

    evidence.append(
        f"Structure agreement: {structure_agreement}."
    )

    evidence.append(
        f"Momentum agreement: {momentum_agreement}."
    )

    # -----------------------------------------
    # Conflict warnings
    # -----------------------------------------

    if agreement == "TIMEFRAME_CONFLICT":

        evidence.append(
            "WARNING: bullish and bearish timeframe "
            "signals are conflicting."
        )

    if structure_agreement == "STRUCTURE_CONFLICT":
    
        evidence.append(
            "WARNING: bullish and bearish market structures "
            "are directly conflicting across timeframes."
        )
    
    elif structure_agreement in [
        "MIXED_STRUCTURE",
        "MOSTLY_BULLISH_STRUCTURE",
        "MOSTLY_BEARISH_STRUCTURE",
    ]:
    
        evidence.append(
            "Market structure is not fully aligned; "
            "directional confidence should remain conservative."
        )

    if momentum_agreement == "MIXED_MOMENTUM":

        evidence.append(
            "WARNING: momentum indicators are not "
            "aligned across timeframes."
        )

    if confirmation == "LOWER_TF_BULLISH_EMERGENCE":

        evidence.append(
            "Bullish movement is developing on lower "
            "timeframes, but the 1h timeframe has not confirmed it."
        )

    if confirmation == "LOWER_TF_BEARISH_EMERGENCE":

        evidence.append(
            "Bearish movement is developing on lower "
            "timeframes, but the 1h timeframe has not confirmed it."
        )

    return evidence


def analyze_multi_timeframe(
    symbol: str,
    timeframe_analysis: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Main multi-timeframe analysis function.
    """

    weighted_score = calculate_weighted_score(
        timeframe_analysis
    )

    overall_bias = determine_overall_bias(
        weighted_score
    )

    agreement = calculate_directional_agreement(
        timeframe_analysis
    )

    structure_agreement = calculate_structure_agreement(
        timeframe_analysis
    )

    momentum_agreement = calculate_momentum_agreement(
        timeframe_analysis
    )

    trend_strength = calculate_trend_strength(
        timeframe_analysis
    )

    confirmation = determine_higher_timeframe_confirmation(
        timeframe_analysis
    )

    market_state = determine_market_state(
        overall_bias,
        confirmation,
        trend_strength,
        structure_agreement,
        momentum_agreement,
    )

    evidence = generate_evidence(
        timeframe_analysis,
        agreement,
        confirmation,
        structure_agreement,
        momentum_agreement,
    )

    return {
        "symbol": symbol,

        "overall_bias": overall_bias,

        "weighted_score": weighted_score,

        "timeframe_agreement": agreement,

        "structure_agreement": structure_agreement,

        "momentum_agreement": momentum_agreement,

        "higher_timeframe_confirmation": confirmation,

        "overall_trend_strength": trend_strength,

        "market_state": market_state,

        "timeframes": timeframe_analysis,

        "evidence": evidence,
    }