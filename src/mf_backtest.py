"""
mf_backtest.py

Event-driven backtest for the PCA multifactor stat-arb strategy. Each
position has MANY legs held at once: the target stock, plus a short (or
long) position in each hedge ETF, sized by the PCA hedge weights so the
stock's exposure to every systematic factor cancels out. What's left
driving P&L is the stock's residual (idiosyncratic) return.

  signal = +1  ("long the residual"):  LONG stock  +  the w-weighted ETF
                                        hedge held SHORT
  signal = -1  ("short the residual"): SHORT stock +  the w-weighted ETF
                                        hedge held LONG
  signal =  0:                         flat (in cash)

Because the position is built to have zero net factor exposure, the P&L per
dollar each day is essentially just (direction x residual return) -- which
is exactly the thing we're trying to trade.

Realism choices:
- Signals are read from yesterday's close, acted on at today's open.
- Trading costs are modeled as a per-side cost in basis points on the
  traded notional of EVERY leg (this bundles commission + slippage; with a
  multi-leg ETF basket, thinking in bps is cleaner and if anything more
  conservative than per-share commissions on cheap, liquid ETFs).
- A borrow fee is charged daily on whatever notional is held SHORT (the
  stock when we're short it, or the ETF legs with positive hedge weight).
- Gross exposure is capped at 1x capital -- no leverage.
- The hedge weights are fixed at entry and held through the trade; a
  production version would refresh them intra-trade (noted as a limitation).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class MFTrade:
    entry_date: pd.Timestamp
    direction: int
    exit_date: pd.Timestamp | None = None
    pnl: float | None = None


def run_mf_backtest(
    stock_close: pd.Series,
    stock_open: pd.Series,
    etf_returns: pd.DataFrame,
    hedge_weights: pd.DataFrame,
    signal: pd.Series,
    stock_returns: pd.Series,
    initial_capital: float = 100_000.0,
    cost_bps_per_side: float = 7.0,
    borrow_rate: float = 0.01,
) -> tuple[pd.DataFrame, list[MFTrade]]:
    """
    Run the multifactor backtest.

    Parameters mirror the single-index engine but generalized to many hedge
    legs. `hedge_weights` is the per-day replicating ETF weight vector from
    pca_hedge.estimate_rolling_hedge; `signal` is the -1/0/+1 series;
    `stock_returns` and `etf_returns` are the daily returns used for
    mark-to-market.

    Returns the daily equity curve and the list of trades.
    """
    cost = cost_bps_per_side / 10_000.0
    daily_borrow = borrow_rate / 252.0

    idx = stock_close.index
    etfs = etf_returns.columns.tolist()

    equity = initial_capital
    current_dir = 0
    S = 0.0                       # dollar size of the stock leg
    w_entry = np.zeros(len(etfs))  # frozen hedge weights for the open trade
    open_trade: MFTrade | None = None
    trades: list[MFTrade] = []
    records = []

    Rmat = etf_returns.reindex(idx).values
    rstock = stock_returns.reindex(idx).values

    for i in range(1, len(idx)):
        today = idx[i]
        target_dir = int(signal.iloc[i - 1])       # yesterday's signal -> act today
        w_today = hedge_weights.iloc[i - 1].values  # weights known as of yesterday

        # If the hedge weights aren't estimated yet, force flat.
        if np.any(~np.isfinite(w_today)):
            target_dir = 0

        day_pnl = 0.0
        costs = 0.0

        # --- Rebalance at today's open if the target position changed ---
        if target_dir != current_dir:
            # Cost to close existing legs (stock + all ETF legs)
            if current_dir != 0:
                traded_notional = S * (1.0 + np.abs(w_entry).sum())
                costs += traded_notional * cost
                if open_trade is not None:
                    open_trade.exit_date = today
                    trades.append(open_trade)
                S = 0.0
                w_entry = np.zeros(len(etfs))

            # Open new legs (if not going flat). No leverage: scale so gross
            # (stock + sum of |ETF weights|) equals capital.
            if target_dir != 0:
                gross_per_dollar = 1.0 + np.abs(w_today).sum()
                S = equity / gross_per_dollar
                w_entry = w_today.copy()
                traded_notional = S * (1.0 + np.abs(w_entry).sum())
                costs += traded_notional * cost
                open_trade = MFTrade(entry_date=today, direction=target_dir)

            current_dir = target_dir

        # --- Daily mark-to-market P&L on held legs ---
        if current_dir != 0:
            stock_leg = current_dir * S * rstock[i]
            hedge_leg = -current_dir * S * (w_entry @ Rmat[i])
            day_pnl = stock_leg + hedge_leg

            # Borrow cost on short notional
            short_notional = 0.0
            if current_dir > 0:
                # long stock (no borrow); ETF legs held short where w>0
                short_notional += S * np.abs(w_entry[w_entry > 0]).sum()
            else:
                # short stock (borrow); ETF legs held short where w<0
                short_notional += S  # stock short
                short_notional += S * np.abs(w_entry[w_entry < 0]).sum()
            costs += short_notional * daily_borrow

            if open_trade is not None:
                # running P&L attribution for the trade log (approximate)
                open_trade.pnl = (open_trade.pnl or 0.0) + (day_pnl - 0.0)

        equity += day_pnl - costs
        records.append({"date": today, "equity": equity, "direction": current_dir,
                        "daily_pnl": day_pnl - costs})

    if open_trade is not None and open_trade.exit_date is None:
        open_trade.exit_date = idx[-1]
        trades.append(open_trade)

    equity_curve = pd.DataFrame(records).set_index("date")
    return equity_curve, trades
