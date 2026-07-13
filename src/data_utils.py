"""
data_utils.py

Data-loading helpers for the PCA multifactor stat-arb strategy: a
multi-ticker close-price fetch (the target stock plus the whole basket of
hedge ETFs, aligned on a common calendar) and a single-ticker OHLCV fetch
(used to get daily opens for realistic next-day-open execution).
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf


def fetch_price_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Download daily OHLCV for a single ticker. Returns lowercase columns:
    open, high, low, close, volume."""
    raw = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if raw.empty:
        raise ValueError(f"No data returned for {ticker} between {start} and {end}.")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    df = raw.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].copy()
    df.index.name = "date"
    return df


def fetch_close_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """
    Download daily adjusted close prices for many tickers at once and align
    them on a common set of trading dates (inner join). Returns a DataFrame
    with one column per ticker.
    """
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    if raw.empty:
        raise ValueError(f"No data returned for {tickers} between {start} and {end}.")

    # yfinance version differences: columns may be "Close" or "close",
    # MultiIndex or flat. Normalize to a flat close-price frame.
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = pd.MultiIndex.from_tuples([(c[0].lower(), c[1]) for c in raw.columns])
        closes = raw["close"].copy()
    else:
        raw.columns = raw.columns.str.lower()
        closes = raw[["close"]].copy()
        closes.columns = tickers

    closes = closes.dropna(how="any")
    closes.index.name = "date"
    return closes
