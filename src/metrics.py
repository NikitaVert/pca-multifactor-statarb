"""
metrics.py

Performance metrics for the PCA multifactor stat-arb strategy:

1. Portfolio-level (off the daily equity curve): total return, CAGR,
   annualized volatility, Sharpe, Sortino, max drawdown.

2. Multifactor neutrality (the headline): the strategy's exposure to the
   market AND to the full set of hedge factors. A single-index strategy
   only proves it's neutral to one index; this proves neutrality to many
   factors at once, which is a stronger claim.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def portfolio_metrics(equity_curve: pd.DataFrame, equity_col: str = "equity") -> dict:
    equity = equity_curve[equity_col]
    daily = equity.pct_change().dropna()

    total_return = equity.iloc[-1] / equity.iloc[0] - 1.0
    n_years = len(equity) / TRADING_DAYS_PER_YEAR
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / n_years) - 1.0 if n_years > 0 else np.nan
    ann_vol = daily.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe = daily.mean() / daily.std() * np.sqrt(TRADING_DAYS_PER_YEAR) if daily.std() > 0 else np.nan
    downside = daily[daily < 0]
    sortino = daily.mean() / downside.std() * np.sqrt(TRADING_DAYS_PER_YEAR) if len(downside) and downside.std() > 0 else np.nan
    dd = (equity / equity.cummax() - 1.0).min()

    return {"total_return": total_return, "cagr": cagr, "annualized_volatility": ann_vol,
            "sharpe_ratio": sharpe, "sortino_ratio": sortino, "max_drawdown": dd}


def market_neutrality(strategy_returns: pd.Series, market_returns: pd.Series) -> dict:
    """Single-factor neutrality vs. the market proxy (e.g. SPY): beta,
    annualized alpha, correlation, R-squared. Beta and correlation near zero
    are the goal."""
    df = pd.concat([strategy_returns, market_returns], axis=1).dropna()
    df.columns = ["strat", "mkt"]
    if len(df) < 2 or df["mkt"].var() == 0:
        return {"beta_to_market": np.nan, "annualized_alpha": np.nan,
                "correlation_to_market": np.nan, "r_squared": np.nan}
    beta = df["strat"].cov(df["mkt"]) / df["mkt"].var()
    alpha_daily = df["strat"].mean() - beta * df["mkt"].mean()
    corr = df["strat"].corr(df["mkt"])
    return {"beta_to_market": beta, "annualized_alpha": alpha_daily * TRADING_DAYS_PER_YEAR,
            "correlation_to_market": corr, "r_squared": corr**2}


def multifactor_neutrality(strategy_returns: pd.Series, factor_returns: pd.DataFrame) -> dict:
    """
    Regress the strategy's returns on the WHOLE basket of hedge factors at
    once (multiple regression) and report:

    - the biggest absolute factor beta (worst-case residual exposure),
    - the R-squared of the full model (how much of the strategy's variance
      ANY combination of factors explains -- low is good),
    - the annualized alpha (intercept), the skill left after removing all
      factor exposure.

    This is the multifactor generalization of the single-index neutrality
    check: it proves the strategy isn't secretly loaded on the market, on
    high-beta, on momentum, or on any other systematic factor.
    """
    df = pd.concat([strategy_returns, factor_returns], axis=1).dropna()
    y = df.iloc[:, 0].values
    X = df.iloc[:, 1:].values
    if len(df) < X.shape[1] + 2:
        return {"max_abs_factor_beta": np.nan, "r_squared": np.nan, "annualized_alpha": np.nan}

    # OLS with intercept
    Xd = np.column_stack([np.ones(len(y)), X])
    coef, *_ = np.linalg.lstsq(Xd, y, rcond=None)
    alpha_daily = coef[0]
    betas = coef[1:]

    resid = y - Xd @ coef
    ss_res = (resid**2).sum()
    ss_tot = ((y - y.mean())**2).sum()
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

    return {"max_abs_factor_beta": float(np.abs(betas).max()),
            "r_squared": float(r2),
            "annualized_alpha": float(alpha_daily * TRADING_DAYS_PER_YEAR)}
