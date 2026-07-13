# PCA Multifactor Statistical Arbitrage

A market-neutral statistical-arbitrage strategy that hedges a target stock
(Costco, COST) against the main systematic factors of the equity market —
extracted via Principal Component Analysis from a diversified basket of
factor ETFs — and trades the residual, idiosyncratic return.

This is the third and most advanced strategy in a progression:
1. Long/flat momentum (single stock, directional).
2. Single-index market-neutral stat-arb (hedged against QQQ).
3. **PCA multifactor market-neutral stat-arb (this repo)** — hedged against
   many systematic factors at once.

## Repo structure

```
.
├── README.md
├── requirements.txt
├── src/
│   ├── data_utils.py     # multi-ticker close fetch + single-ticker OHLCV fetch
│   ├── pca_hedge.py      # rolling PCA factor extraction, hedge weights, residual
│   ├── mf_backtest.py    # multifactor (multi-leg) backtest engine
│   └── metrics.py        # portfolio + single- and multi-factor neutrality metrics
├── notebooks/
│   └── 05_pca_multifactor_statarb.ipynb   # end-to-end
└── writeup/
    └── PCA_Multifactor_Writeup.md
```

## How to run

1. `pip install -r requirements.txt`
2. Run `notebooks/05_pca_multifactor_statarb.ipynb` end-to-end. One manual
   step: Section 3 tests both momentum and reversal directions; set
   `DIRECTION` in Section 4 to whichever had the better gross Sharpe.
3. The target stock (`STOCK`) and hedge basket (`ETFS`) are configuration
   lines at the top — the framework applies to any chosen stock.

## Key ideas

- **Multifactor hedge, not single-index.** Hedges against the market plus
  size, value, momentum, and high-beta/low-vol factors simultaneously,
  isolating a cleaner idiosyncratic residual.
- **PCA for stability.** The hedge ETFs are collinear; PCA extracts
  orthogonal factors so the hedge ratios are stable (principal component
  regression).
- **Neutrality proven across all factors.** The strategy's exposure to
  every factor, not just the market, is measured and shown to be near zero.
- **Deliberate design choices.** Costco chosen for structural reasons
  (trended up, fundamentals-driven, moderate index weight, not
  options-dominated); sector ETFs excluded to avoid self-hedging.

Full rationale, results, and limitations are in
[`writeup/PCA_Multifactor_Writeup.md`](writeup/PCA_Multifactor_Writeup.md).
