"""
Backtesting engine for the NIFTY / BANKNIFTY
multi-timeframe market analysis system.

IMPORTANT:
This project currently uses synthetic data.

The backtester is intended to validate:
    - point-in-time analysis
    - signal generation
    - trade execution
    - risk management
    - performance reporting

Synthetic results must NOT be interpreted
as evidence of real-world profitability.
"""

import pandas as pd

from data_provider import DummyDataProvider
from indicators import compute_all
from trend_analyzer import analyze_trend
from multi_timeframe_analyzer import (
    analyze_multi_timeframe
)


# ============================================================
# SETTINGS
# ============================================================

TIMEFRAMES = {
    "1h": 60,
    "15m": 15,
    "5m": 5,
}

INITIAL_CAPITAL = 100000.0

STOP_LOSS_PCT = 0.005
TAKE_PROFIT_PCT = 0.010

POSITION_SIZE = 1

# Simple placeholder assumptions for testing.
# These are NOT broker-specific costs.
SLIPPAGE_PCT = 0.0002
TRANSACTION_COST_PCT = 0.0003


# ============================================================
# POINT-IN-TIME ANALYSIS
# ============================================================

def get_analysis_at_time(
    provider,
    symbol_key,
    timestamp
):
    """
    Build multi-timeframe analysis using only
    information available at the given timestamp.
    """

    timeframe_analysis = {}

    for timeframe, minutes in TIMEFRAMES.items():

        df = provider.get_candles_asof(
            symbol_key,
            minutes,
            timestamp
        )

        if df.empty:
            return None

        df = compute_all(df)

        if len(df) < 60:
            return None

        analysis = analyze_trend(df)

        timeframe_analysis[timeframe] = analysis

    return analyze_multi_timeframe(
        symbol_key,
        timeframe_analysis
    )


# ============================================================
# SIGNAL DECISION
# ============================================================

def determine_position_decision(
    analysis
):
    """
    Convert the multi-timeframe analysis into:

        LONG
        EXIT
        HOLD

    The LLM is NOT involved in this decision.
    """

    if analysis is None:
        return "HOLD"

    overall_bias = analysis.get(
        "overall_bias",
        "NEUTRAL"
    )

    confirmation = analysis.get(
        "higher_timeframe_confirmation",
        ""
    )

    market_state = analysis.get(
        "market_state",
        ""
    )

    bullish_confirmation = [
        "FULL_BULLISH_CONFIRMATION",
        "PARTIAL_BULLISH_CONFIRMATION",
        "LOWER_TF_BULLISH_EMERGENCE",
    ]

    bearish_states = [
        "BEARISH_WITH_CONFIRMATION",
        "STRONG_BEARISH_ENVIRONMENT",
    ]

    if (
        overall_bias in [
            "BULLISH",
            "STRONGLY_BULLISH",
        ]
        and confirmation in bullish_confirmation
        and market_state not in bearish_states
    ):
        return "LONG"

    if overall_bias in [
        "BEARISH",
        "STRONGLY_BEARISH",
    ]:
        return "EXIT"

    return "HOLD"


# ============================================================
# EXECUTION COSTS
# ============================================================

def apply_entry_cost(price):
    """
    Simulate adverse slippage and transaction cost
    on entry.
    """

    slippage = price * SLIPPAGE_PCT
    cost = price * TRANSACTION_COST_PCT

    return price + slippage + cost


def apply_exit_cost(price):
    """
    Simulate adverse slippage and transaction cost
    on exit.
    """

    slippage = price * SLIPPAGE_PCT
    cost = price * TRANSACTION_COST_PCT

    return price - slippage - cost


# ============================================================
# STOP LOSS / TAKE PROFIT
# ============================================================

def check_stop_or_target(
    position,
    candle
):
    """
    Check whether SL or TP was reached.

    Conservative assumption:
    If both are touched in one candle,
    SL is assumed to occur first.
    """

    entry_price = position[
        "entry_price"
    ]

    stop_price = (
        entry_price
        * (1 - STOP_LOSS_PCT)
    )

    target_price = (
        entry_price
        * (1 + TAKE_PROFIT_PCT)
    )

    if candle["low"] <= stop_price:

        return "STOP", stop_price

    if candle["high"] >= target_price:

        return "TARGET", target_price

    return None, None


# ============================================================
# CLOSE POSITION
# ============================================================

def close_position(
    position,
    raw_exit_price,
    exit_time,
    reason
):
    """
    Close a long position and calculate P&L.
    """

    exit_price = apply_exit_cost(
        raw_exit_price
    )

    entry_price = position[
        "entry_price"
    ]

    pnl = (
        exit_price - entry_price
    ) * POSITION_SIZE

    return {
        "entry_time":
            position["entry_time"],

        "entry_price":
            entry_price,

        "exit_time":
            exit_time,

        "exit_price":
            exit_price,

        "reason":
            reason,

        "pnl":
            pnl,
    }


# ============================================================
# BACKTEST
# ============================================================

def run_backtest(symbol_key):

    provider = DummyDataProvider()

    print()
    print("=" * 60)
    print(
        f"Running backtest: {symbol_key}"
    )
    print("=" * 60)

    base_5m = provider.get_candles(
        symbol_key,
        5
    )

    if base_5m.empty:
        raise ValueError(
            f"No 5m data available for {symbol_key}"
        )

    timestamps = base_5m[
        "timestamp"
    ].tolist()

    capital = INITIAL_CAPITAL

    position = None

    trades = []

    equity_records = []

    # --------------------------------------------------------
    # Walk forward through historical data
    # --------------------------------------------------------

    for i in range(
        len(timestamps) - 1
    ):

        timestamp = timestamps[i]

        candle = base_5m.iloc[i]

        # ====================================================
        # EXISTING POSITION
        # ====================================================

        if position is not None:

            # ------------------------------------------------
            # Check SL / TP
            # ------------------------------------------------

            reason, exit_price = (
                check_stop_or_target(
                    position,
                    candle
                )
            )

            if reason is not None:

                trade = close_position(
                    position,
                    exit_price,
                    timestamp,
                    reason
                )

                capital += trade["pnl"]

                trades.append(trade)

                position = None

                equity_records.append({
                    "timestamp":
                        timestamp,

                    "equity":
                        capital,
                })

                continue

            # ------------------------------------------------
            # Check strategy exit signal
            # ------------------------------------------------

            analysis = get_analysis_at_time(
                provider,
                symbol_key,
                timestamp
            )

            decision = (
                determine_position_decision(
                    analysis
                )
            )

            if decision == "EXIT":

                trade = close_position(
                    position,
                    candle["close"],
                    timestamp,
                    "SIGNAL_EXIT"
                )

                capital += trade["pnl"]

                trades.append(trade)

                position = None

                equity_records.append({
                    "timestamp":
                        timestamp,

                    "equity":
                        capital,
                })

                continue

        # ====================================================
        # NEW ENTRY
        # ====================================================

        if position is None:

            analysis = get_analysis_at_time(
                provider,
                symbol_key,
                timestamp
            )

            decision = (
                determine_position_decision(
                    analysis
                )
            )

            if decision == "LONG":

                # ------------------------------------------------
                # Execute on NEXT candle open.
                # This prevents same-candle look-ahead.
                # ------------------------------------------------

                next_candle = (
                    base_5m.iloc[i + 1]
                )

                raw_entry_price = (
                    next_candle["open"]
                )

                entry_price = (
                    apply_entry_cost(
                        raw_entry_price
                    )
                )

                position = {
                    "entry_time":
                        next_candle[
                            "timestamp"
                        ],

                    "entry_price":
                        entry_price,
                }

        # ----------------------------------------------------
        # Record current equity
        # ----------------------------------------------------

        unrealized_pnl = 0.0

        if position is not None:

            unrealized_pnl = (
                candle["close"]
                - position["entry_price"]
            ) * POSITION_SIZE

        equity_records.append({
            "timestamp":
                timestamp,

            "equity":
                capital + unrealized_pnl,
        })

    # ========================================================
    # CLOSE REMAINING POSITION
    # ========================================================

    if position is not None:

        final_candle = (
            base_5m.iloc[-1]
        )

        trade = close_position(
            position,
            final_candle["close"],
            final_candle["timestamp"],
            "END_OF_DATA"
        )

        capital += trade["pnl"]

        trades.append(trade)

        equity_records.append({
            "timestamp":
                final_candle["timestamp"],

            "equity":
                capital,
        })

    return (
        capital,
        trades,
        equity_records
    )


# ============================================================
# PERFORMANCE METRICS
# ============================================================

def calculate_metrics(
    final_capital,
    trades,
    equity_records
):

    net_pnl = (
        final_capital
        - INITIAL_CAPITAL
    )

    return_pct = (
        net_pnl
        / INITIAL_CAPITAL
        * 100
    )

    total_trades = len(trades)

    wins = [
        trade
        for trade in trades
        if trade["pnl"] > 0
    ]

    losses = [
        trade
        for trade in trades
        if trade["pnl"] < 0
    ]

    if total_trades > 0:

        win_rate = (
            len(wins)
            / total_trades
            * 100
        )

    else:

        win_rate = 0.0

    total_profit = sum(
        trade["pnl"]
        for trade in wins
    )

    total_loss = abs(
        sum(
            trade["pnl"]
            for trade in losses
        )
    )

    if total_loss > 0:

        profit_factor = (
            total_profit
            / total_loss
        )

    else:

        profit_factor = None

    if wins:

        average_win = (
            total_profit
            / len(wins)
        )

    else:

        average_win = 0.0

    if losses:

        average_loss = (
            -total_loss
            / len(losses)
        )

    else:

        average_loss = 0.0

    # --------------------------------------------------------
    # Maximum drawdown
    # --------------------------------------------------------

    if equity_records:

        equity_df = pd.DataFrame(
            equity_records
        )

        equity_df[
            "peak"
        ] = equity_df[
            "equity"
        ].cummax()

        equity_df[
            "drawdown"
        ] = (
            equity_df["equity"]
            - equity_df["peak"]
        )

        max_drawdown = (
            equity_df["drawdown"].min()
        )

    else:

        max_drawdown = 0.0

    return {
        "initial_capital":
            INITIAL_CAPITAL,

        "final_capital":
            final_capital,

        "net_pnl":
            net_pnl,

        "return_pct":
            return_pct,

        "total_trades":
            total_trades,

        "winning_trades":
            len(wins),

        "losing_trades":
            len(losses),

        "win_rate":
            win_rate,

        "average_win":
            average_win,

        "average_loss":
            average_loss,

        "profit_factor":
            profit_factor,

        "max_drawdown":
            max_drawdown,
    }


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(
    symbol_key,
    trades,
    equity_records
):

    if trades:

        trades_df = pd.DataFrame(
            trades
        )

        trades_df.to_csv(
            f"{symbol_key}_backtest_trades.csv",
            index=False
        )

    if equity_records:

        equity_df = pd.DataFrame(
            equity_records
        )

        equity_df.to_csv(
            f"{symbol_key}_equity_curve.csv",
            index=False
        )


# ============================================================
# PRINT RESULTS
# ============================================================

def print_results(
    symbol_key,
    metrics
):

    print()
    print("=" * 60)
    print(
        f"BACKTEST RESULTS: {symbol_key}"
    )
    print("=" * 60)

    print(
        f"Initial capital : "
        f"₹{metrics['initial_capital']:,.2f}"
    )

    print(
        f"Final capital   : "
        f"₹{metrics['final_capital']:,.2f}"
    )

    print(
        f"Net P&L         : "
        f"₹{metrics['net_pnl']:,.2f}"
    )

    print(
        f"Return          : "
        f"{metrics['return_pct']:.2f}%"
    )

    print(
        f"Total trades    : "
        f"{metrics['total_trades']}"
    )

    print(
        f"Win rate        : "
        f"{metrics['win_rate']:.2f}%"
    )

    print(
        f"Winning trades  : "
        f"{metrics['winning_trades']}"
    )

    print(
        f"Losing trades   : "
        f"{metrics['losing_trades']}"
    )

    print(
        f"Average win     : "
        f"₹{metrics['average_win']:.2f}"
    )

    print(
        f"Average loss    : "
        f"₹{metrics['average_loss']:.2f}"
    )

    if metrics["profit_factor"] is not None:

        print(
            f"Profit factor   : "
            f"{metrics['profit_factor']:.2f}"
        )

    else:

        print(
            "Profit factor   : N/A"
        )

    print(
        f"Max drawdown    : "
        f"₹{metrics['max_drawdown']:.2f}"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    for symbol in [
        "NIFTY",
        "BANKNIFTY"
    ]:

        (
            final_capital,
            trades,
            equity_records
        ) = run_backtest(
            symbol
        )

        metrics = calculate_metrics(
            final_capital,
            trades,
            equity_records
        )

        print_results(
            symbol,
            metrics
        )

        save_results(
            symbol,
            trades,
            equity_records
        )

        print()
        print(
            f"Saved: "
            f"{symbol}_backtest_trades.csv"
        )

        print(
            f"Saved: "
            f"{symbol}_equity_curve.csv"
        )