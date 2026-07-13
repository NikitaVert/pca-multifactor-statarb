"""
pca_hedge.py

The heart of the multifactor strategy: instead of hedging the target stock
against a single index (a shortcut), we hedge it against the main
systematic FACTORS extracted from a diversified basket of ETFs, using
Principal Component Analysis (PCA).

Why PCA
-------
The hedge ETFs (SPY, QQQ, IWM, SPHB, SPLV, MTUM, VLUE) are highly
correlated with each other -- they all rise and fall with the broad market.
If you regressed the stock directly on all seven, the overlapping
information (multicollinearity) would give unstable, untrustworthy hedge
ratios. PCA fixes this by extracting a small number of INDEPENDENT
underlying movements ("principal components" / factors) that drive most of
the basket's variance:

  - PC1 is almost always "the whole market" (everything moving together).
  - PC2, PC3, ... capture style tilts (e.g. high-beta vs. low-beta,
    growth vs. value).

We hedge the stock against these clean, orthogonal factors instead of the
tangled raw ETFs. This is the standard professional approach to
multifactor hedging (principal component regression).

The math (per rebalance, using only trailing data)
--------------------------------------------------
Let R be the trailing window of ETF returns (window x N).
  1. Demean R, form covariance Sigma = cov(R).
  2. Eigen-decompose Sigma; keep the top K eigenvectors V_K (N x K) that
     explain >= var_threshold of the variance. These are the factor
     directions.
  3. Factor returns over the window: F = R_demeaned @ V_K (window x K).
  4. Regress the stock's returns on F to get factor exposures beta_F (K).
     (F's columns are orthogonal, so this regression is stable.)
  5. The stock's systematic return = F @ beta_F = R_demeaned @ (V_K @ beta_F).
     So the replicating hedge portfolio holds ETF weights  w = V_K @ beta_F.

Holding the stock long and the w-weighted ETF basket short cancels the
stock's exposure to ALL K factors at once, leaving only its residual
(idiosyncratic) return -- the part we actually want to trade.

Everything uses trailing windows only, so there is no look-ahead leakage.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_returns(close_prices: pd.DataFrame) -> pd.DataFrame:
    """Simple daily returns for every column."""
    return close_prices.pct_change().dropna()


def _hedge_weights_one_window(
    R_win: np.ndarray,
    r_win: np.ndarray,
    var_threshold: float,
    max_components: int,
    min_components: int = 3,
) -> tuple[np.ndarray, int]:
    """
    Given a trailing window of ETF returns (R_win: T x N) and the stock's
    returns (r_win: T), return the replicating ETF hedge weights w (N) and
    the number of principal components used.
    """
    # 1. Demean
    R_mean = R_win.mean(axis=0)
    Rc = R_win - R_mean
    rc = r_win - r_win.mean()

    # 2. Covariance + eigendecomposition (eigh: ascending eigenvalues)
    Sigma = np.cov(Rc, rowvar=False)
    eigvals, eigvecs = np.linalg.eigh(Sigma)

    # Sort descending
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]
    eigvals = np.clip(eigvals, 0.0, None)

    # 3. Choose K to reach the variance threshold (at least 1, at most max)
    total = eigvals.sum()
    if total <= 0:
        return np.zeros(R_win.shape[1]), 0
    cum = np.cumsum(eigvals) / total
    K = int(np.searchsorted(cum, var_threshold) + 1)
    K = max(min_components, K)
    K = max(1, min(K, max_components, eigvecs.shape[1]))

    V_K = eigvecs[:, :K]              # N x K factor directions
    F = Rc @ V_K                      # T x K factor returns

    # 4. Regress stock on factors (orthogonal columns -> stable)
    #    beta_F = (F'F)^-1 F' rc
    FtF = F.T @ F
    beta_F = np.linalg.solve(FtF, F.T @ rc)

    # 5. Replicating ETF weights
    w = V_K @ beta_F                  # N
    return w, K


def estimate_rolling_hedge(
    etf_returns: pd.DataFrame,
    stock_returns: pd.Series,
    window: int = 60,
    var_threshold: float = 0.95,
    max_components: int = 5,
    min_components: int = 3,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Roll through time estimating the PCA hedge on each day's trailing window.

    Returns
    -------
    weights : DataFrame (dates x ETFs)
        The replicating hedge weight for each ETF on each day. The hedge for
        day t is estimated from the window ENDING at t-1, so it can be
        applied to day t without look-ahead.
    residual : Series
        The stock's idiosyncratic return each day: r_stock - w . r_etf,
        using that day's (trailing-estimated) weights. This is what the
        trading signal is built on.
    n_components : Series
        How many principal components were used each day (for diagnostics).
    """
    etfs = etf_returns.columns.tolist()
    idx = stock_returns.index
    R = etf_returns.values
    r = stock_returns.values

    weights = np.full((len(idx), len(etfs)), np.nan)
    residual = np.full(len(idx), np.nan)
    ncomp = np.full(len(idx), np.nan)

    for t in range(window, len(idx)):
        R_win = R[t - window : t]     # rows up to t-1
        r_win = r[t - window : t]
        w, K = _hedge_weights_one_window(R_win, r_win, var_threshold, max_components, min_components)
        weights[t] = w
        ncomp[t] = K
        # residual on day t using trailing-estimated weights applied to
        # day t's actual returns
        residual[t] = r[t] - w @ R[t]

    weights_df = pd.DataFrame(weights, index=idx, columns=etfs)
    residual_s = pd.Series(residual, index=idx, name="residual")
    ncomp_s = pd.Series(ncomp, index=idx, name="n_components")
    return weights_df, residual_s, ncomp_s


def compute_signal(
    residual_ret: pd.Series,
    lookback: int = 21,
    skip: int = 1,
    entry_z: float = 0.5,
    direction: str = "momentum",
) -> pd.DataFrame:
    """
    Turn the residual-return series into a -1 / 0 / +1 position signal, using
    the same z-scored cumulative-residual logic as the single-index version.

    - Sum residuals over a trailing `lookback` window, skipping the most
      recent `skip` day(s) (short-term residuals tend to reverse).
    - Standardize into a z-score with rolling one-year volatility, so the
      threshold means the same thing in calm and wild periods.
    - Enter the spread only when |z| > entry_z; otherwise stay flat.

    direction "momentum": +1 when residual has been positive, -1 when negative.
    direction "reversal": the opposite. Both are tested so the data decides.
    """
    cum = residual_ret.shift(skip).rolling(lookback).sum()
    z = cum / cum.rolling(252).std()

    raw = pd.Series(0, index=residual_ret.index, dtype=int)
    raw[z > entry_z] = 1
    raw[z < -entry_z] = -1

    if direction == "reversal":
        raw = -raw
    elif direction != "momentum":
        raise ValueError("direction must be 'momentum' or 'reversal'")

    return pd.DataFrame({"cum_residual": cum, "residual_z": z, "signal": raw})
