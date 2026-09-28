"""
NIFTY / BANKNIFTY Market Intelligence Dashboard

This application combines:
    - Multi-timeframe technical analysis
    - Trend and market-structure analysis
    - Backtest results
    - AI-generated explanation

IMPORTANT:
The AI explains the deterministic analysis.
It does NOT independently generate trading signals.

Current market data mode:
    Synthetic data

This project is for research/software experimentation.
Synthetic backtests do not demonstrate real-world profitability.
"""

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from data_provider import DummyDataProvider
from indicators import compute_all
from trend_analyzer import analyze_trend
from multi_timeframe_analyzer import (
    analyze_multi_timeframe
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="NIFTY Market Agent",
    page_icon="📈",
    layout="wide"
)


# ============================================================
# CUSTOM HEADER
# ============================================================

st.title(
    "📈 NIFTY / BANKNIFTY Market Intelligence Agent"
)

st.caption(
    "Multi-timeframe technical analysis, market structure "
    "and AI-assisted market interpretation"
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("Analysis Settings")

symbol = st.sidebar.selectbox(
    "Select Index",
    [
        "NIFTY",
        "BANKNIFTY"
    ]
)

run_analysis = st.sidebar.button(
    "🔄 Refresh Analysis",
    width="stretch"
)


# ============================================================
# ANALYSIS FUNCTION
# ============================================================

def run_market_analysis(symbol):

    provider = DummyDataProvider()

    timeframe_analysis = {}

    timeframes = {
        "1h": 60,
        "15m": 15,
        "5m": 5
    }

    for timeframe, minutes in timeframes.items():

        df = provider.get_candles(
            symbol,
            minutes
        )

        df = compute_all(df)

        analysis = analyze_trend(
            df
        )

        timeframe_analysis[
            timeframe
        ] = analysis

    overall = analyze_multi_timeframe(
        symbol,
        timeframe_analysis
    )

    return overall, timeframe_analysis


# ============================================================
# AI EXPLANATION
# ============================================================

def generate_ai_explanation(
    symbol,
    overall,
    timeframe_analysis
):
    """
    Ask the LLM to explain the already-computed
    deterministic market analysis.

    The LLM is explicitly instructed NOT to invent
    a new trading signal.
    """

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:

        return (
            "AI explanation unavailable.\n\n"
            "Add OPENAI_API_KEY to your .env file "
            "to enable this feature."
        )

    model = os.getenv(
        "OPENAI_MODEL",
        "gpt-5.6-luna"
    )

    client = OpenAI(
        api_key=api_key
    )

    analysis_payload = {
        "symbol": symbol,

        "overall_bias":
            overall.get(
                "overall_bias"
            ),

        "weighted_score":
            overall.get(
                "weighted_score"
            ),

        "market_state":
            overall.get(
                "market_state"
            ),

        "timeframe_agreement":
            overall.get(
                "timeframe_agreement"
            ),

        "structure_agreement":
            overall.get(
                "structure_agreement"
            ),

        "momentum_agreement":
            overall.get(
                "momentum_agreement"
            ),

        "higher_timeframe_confirmation":
            overall.get(
                "higher_timeframe_confirmation"
            ),

        "overall_trend_strength":
            overall.get(
                "overall_trend_strength"
            ),

        "timeframes":
            timeframe_analysis,

        "evidence":
            overall.get(
                "evidence",
                []
            ),
    }

    prompt = f"""
You are the explanation layer of a market intelligence
software system.

Your job is to explain the technical analysis that has
ALREADY been calculated by the deterministic analysis engine.

Do NOT:
- invent indicators
- invent prices
- invent signals
- claim certainty
- make guaranteed profit claims
- override the calculated market bias
- provide personalized financial advice

Explain the result clearly for a technical user.

Mention:
1. Overall market interpretation
2. What the 1h timeframe says
3. What the 15m timeframe says
4. What the 5m timeframe says
5. Whether the timeframes agree or conflict
6. Momentum / structure considerations
7. Important caution or uncertainty

Keep the explanation concise and readable.

Calculated analysis:

{analysis_payload}
"""

    try:

        response = client.responses.create(
            model=model,
            input=prompt
        )

        return response.output_text

    except Exception as exc:

        return (
            "AI explanation could not be generated.\n\n"
            f"Reason: {exc}"
        )


# ============================================================
# LOAD MARKET ANALYSIS
# ============================================================

overall, timeframe_analysis = (
    run_market_analysis(symbol)
)


# ============================================================
# MARKET OVERVIEW
# ============================================================

st.header(
    f"{symbol} Market View"
)

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Overall Bias",
    overall.get(
        "overall_bias",
        "N/A"
    )
)

col2.metric(
    "Market State",
    overall.get(
        "market_state",
        "N/A"
    )
)

col3.metric(
    "Trend Strength",
    overall.get(
        "overall_trend_strength",
        "N/A"
    )
)

col4.metric(
    "Weighted Score",
    f"{overall.get('weighted_score', 0):.2f}"
)


# ============================================================
# MULTI-TIMEFRAME ANALYSIS
# ============================================================

st.subheader(
    "⏱️ Multi-Timeframe Analysis"
)

columns = st.columns(3)

for column, timeframe in zip(
    columns,
    ["1h", "15m", "5m"]
):

    analysis = timeframe_analysis[
        timeframe
    ]

    with column:

        st.markdown(
            f"### {timeframe}"
        )

        st.metric(
            "Bias",
            analysis.get(
                "bias",
                "N/A"
            )
        )

        st.write(
            "**Trend:**",
            analysis.get(
                "trend_strength",
                "N/A"
            )
        )

        st.write(
            "**Structure:**",
            analysis.get(
                "structure",
                "N/A"
            )
        )

        rsi = analysis.get(
            "rsi"
        )

        adx = analysis.get(
            "adx"
        )

        if isinstance(
            rsi,
            (int, float)
        ):

            st.write(
                f"**RSI:** {rsi:.2f}"
            )

        else:

            st.write(
                "**RSI:** N/A"
            )

        if isinstance(
            adx,
            (int, float)
        ):

            st.write(
                f"**ADX:** {adx:.2f}"
            )

        else:

            st.write(
                "**ADX:** N/A"
            )


# ============================================================
# MARKET STRUCTURE
# ============================================================

st.subheader(
    "🧭 Market Structure & Confirmation"
)

c1, c2 = st.columns(2)

with c1:

    st.write(
        "**Timeframe Agreement**"
    )

    st.info(
        overall.get(
            "timeframe_agreement",
            "N/A"
        )
    )

    st.write(
        "**Structure Agreement**"
    )

    st.info(
        overall.get(
            "structure_agreement",
            "N/A"
        )
    )

    st.write(
        "**Momentum Agreement**"
    )

    st.info(
        overall.get(
            "momentum_agreement",
            "N/A"
        )
    )


with c2:

    st.write(
        "**Higher-Timeframe Confirmation**"
    )

    st.info(
        overall.get(
            "higher_timeframe_confirmation",
            "N/A"
        )
    )

    st.write(
        "**Overall Trend Strength**"
    )

    st.info(
        overall.get(
            "overall_trend_strength",
            "N/A"
        )
    )


# ============================================================
# EVIDENCE
# ============================================================

st.subheader(
    "🔎 Analysis Evidence"
)

for evidence in overall.get(
    "evidence",
    []
):

    st.write(
        f"• {evidence}"
    )


# ============================================================
# AI EXPLANATION
# ============================================================

st.divider()

st.header(
    "🤖 AI Market Interpretation"
)

st.caption(
    "The AI explains the deterministic technical analysis; "
    "it does not independently generate the market signal."
)

if st.button(
    "✨ Generate AI Explanation",
    width="stretch"
):

    with st.spinner(
        "Generating market interpretation..."
    ):

        explanation = (
            generate_ai_explanation(
                symbol,
                overall,
                timeframe_analysis
            )
        )

    st.markdown(
        explanation
    )

else:

    st.info(
        "Click 'Generate AI Explanation' to have the "
        "AI summarize the current multi-timeframe analysis."
    )


# ============================================================
# BACKTEST RESULTS
# ============================================================

st.divider()

st.header(
    "📊 Backtest Results"
)

trades_file = (
    f"{symbol}_backtest_trades.csv"
)

equity_file = (
    f"{symbol}_equity_curve.csv"
)

try:

    trades = pd.read_csv(
        trades_file
    )

    equity = pd.read_csv(
        equity_file
    )

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    total_trades = len(
        trades
    )

    winning_trades = int(
        (
            trades["pnl"] > 0
        ).sum()
    )

    losing_trades = int(
        (
            trades["pnl"] < 0
        ).sum()
    )

    net_pnl = trades[
        "pnl"
    ].sum()

    if total_trades > 0:

        win_rate = (
            winning_trades
            / total_trades
            * 100
        )

    else:

        win_rate = 0

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Trades",
        total_trades
    )

    c2.metric(
        "Win Rate",
        f"{win_rate:.1f}%"
    )

    c3.metric(
        "Winning Trades",
        winning_trades
    )

    c4.metric(
        "Net P&L",
        f"₹{net_pnl:,.2f}"
    )

    # --------------------------------------------------------
    # Equity curve
    # --------------------------------------------------------

    st.subheader(
        "Equity Curve"
    )

    equity[
        "timestamp"
    ] = pd.to_datetime(
        equity["timestamp"]
    )

    equity = equity.set_index(
        "timestamp"
    )

    st.line_chart(
        equity["equity"],
        width="stretch"
    )

    # --------------------------------------------------------
    # Trade table
    # --------------------------------------------------------

    st.subheader(
        "Trade Log"
    )

    st.dataframe(
        trades,
        width="stretch",
        hide_index=True
    )

except FileNotFoundError:

    st.warning(
        "Backtest CSV files were not found. "
        "Run backtester.py first."
    )


# ============================================================
# SYSTEM ARCHITECTURE
# ============================================================

st.divider()

st.header(
    "🏗️ System Architecture"
)

st.code(
    """
Market Data
    │
    ├── Synthetic Data
    └── Groww API
          │
          ▼
    Data Provider
          │
          ▼
    Indicator Engine
    ├── EMA
    ├── RSI
    ├── MACD
    ├── ATR
    ├── ADX
    ├── Bollinger Bands
    └── VWAP
          │
          ▼
    Trend Analyzer
          │
          ▼
    Multi-Timeframe Analyzer
    ├── 1H Macro Direction
    ├── 15M Confirmation
    └── 5M Timing
          │
          ▼
    Deterministic Market View
          │
          ├───────────────┐
          ▼               ▼
    Dashboard       AI Explanation
                          │
                          ▼
                    Human-readable
                    interpretation
    """,
    language="text"
)


# ============================================================
# DISCLAIMER
# ============================================================

st.divider()

st.caption(
    "⚠️ Research / software experimentation only. "
    "The current dashboard uses synthetic market data. "
    "Synthetic backtest results do not demonstrate "
    "real-world profitability. Real deployment would "
    "require appropriate historical data, out-of-sample "
    "testing, transaction-cost modelling, slippage "
    "modelling and risk controls."
)