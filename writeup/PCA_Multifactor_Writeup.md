# PCA Multifactor Statistical Arbitrage

*A market-neutral statistical-arbitrage strategy that hedges a target stock against the main systematic factors of the equity market — extracted via Principal Component Analysis from a diversified basket of factor ETFs — and trades the residual, idiosyncratic return.*

## Motivation: beyond a single-index hedge

An earlier version of this strategy hedged the target stock against a single index (QQQ). That is a practical shortcut, but a shortcut: it removes the broad market, yet leaves the stock exposed to other systematic forces — high-beta/volatility risk, size, value, and momentum factors. Any "residual" left after a single-index hedge still contains those systematic exposures, which are not genuinely stock-specific and can dominate the signal.

This version hedges against the main systematic factors of the market simultaneously. It draws them from a diversified basket of factor ETFs and uses Principal Component Analysis to reduce that basket to a handful of independent underlying factors, then neutralizes all of them at once. The residual that remains is a cleaner estimate of the stock's true idiosyncratic return.

## Two deliberate design choices

**The stock: Costco (COST), not Tesla.** Tesla's price is heavily influenced by its enormous options market, whose dealer-hedging feedback loops make TSLA's idiosyncratic moves unusual and difficult to generalize — a poor subject for isolating a "normal" residual. Costco trended up steadily over the sample, is driven by ordinary fundamentals (membership growth, comparable sales, earnings), and is a moderate index weight rather than a top-five constituent. That last point matters: hedging a mega-cap like Apple against broad indices partly hedges the stock against itself, because it is a large fraction of those indices. A moderate-weight name avoids this circularity. The ticker is a single configuration line, so the framework applies to any chosen stock.

**The hedge basket: diversified factor ETFs, no single-sector ETFs.** The basket is SPY (market), IWM (size), QQQ (growth/tech tilt), SPHB (high beta), SPLV (low volatility), MTUM (momentum), and VLUE (value) — spanning the market plus the principal style and risk factors. Single-sector ETFs are deliberately excluded: Costco is a large weight in the consumer-staples sector ETF, so hedging against it would reintroduce the self-hedging problem. Diversified factor ETFs each contain the target stock at negligible weight, so they hedge the systematic factors without that contamination.

## Methodology

- **Factor extraction (PCA).** The hedge ETFs are highly correlated with one another, so regressing the stock directly on all seven would produce unstable, collinear hedge ratios. Each day, on a trailing 60-day window, PCA extracts the top principal components of the ETF basket — the independent underlying movements that drive most of its variance. The first is essentially the whole market; the next few capture style tilts. At least three components are retained (market plus two style factors); more are used if needed to reach 95% of the basket's variance.
- **Hedge construction.** The stock's returns are regressed on the extracted factors to measure its exposure to each. Because the components are orthogonal, this regression is stable. The exposures are then mapped back into a replicating portfolio of the underlying ETFs. Holding the stock long and this ETF portfolio short cancels the stock's exposure to every retained factor at once, leaving the residual.
- **Signal.** The residual returns are summed over a trailing month (skipping the most recent day, since short-term residuals tend to reverse), standardized into a z-score using rolling volatility, and traded when the z-score clears a threshold — long the residual spread when it is significantly positive, short when significantly negative, flat otherwise. Both momentum and reversal directions are tested; the data decides.
- **Execution realism.** Signals are read from yesterday's close and acted on at today's open. Trading costs are charged as a per-side cost in basis points on every leg's traded notional (bundling commission and slippage, which is cleaner and if anything more conservative for a multi-leg ETF basket). A borrow fee is charged daily on all short notional. Gross exposure is capped at 1× capital — no leverage.
- **Validation.** Everything is estimated on trailing windows only (no look-ahead). Parameters are fixed a priori using standard conventions. The data is split at 2022-01-01 and the strategy is re-estimated and rerun independently on each half, checking both that neutrality holds and whether the alpha survives out-of-sample.

## Results

Backtest period: **2015-01-02 to 2025-08-29**. Over this sample COST rose **725%** — a clean, steady uptrend, confirming the stock-selection rationale.

### Hedge diagnostics (Section 2)

The PCA retained **3.2 principal components on average** (range 3–4), i.e. the market plus two to three style factors. The average replicating hedge weights were:

| ETF | Avg. weight | Factor represented |
|---|---|---|
| SPLV | 0.377 | Low volatility |
| MTUM | 0.217 | Momentum |
| SPY | 0.203 | Market |
| QQQ | 0.182 | Growth / tech |
| VLUE | 0.070 | Value |
| IWM | −0.074 | Size |
| SPHB | −0.111 | High beta |

This is an economically meaningful result worth noting: the hedge assigns its **largest weight to the low-volatility factor (SPLV) and a negative weight to high-beta (SPHB)**. The PCA was never told anything about Costco's character — it inferred from returns alone that COST behaves like a defensive, low-volatility name. The hedge is finding something real, not fitting noise.

### Direction test (Section 3)

| Direction | Gross Sharpe | Gross cum. return | Signal changes |
|---|---|---|---|
| Momentum | 0.045 | −3.3% | 353 |
| Reversal | −0.045 | −15.0% | 353 |

**The signal has no predictive value.** A gross Sharpe of 0.045 — measured *before any trading costs* — is indistinguishable from zero. The two directions are exact mirror images, which means this was not a choice between two competing hypotheses but between two readings of the same noise. Selecting "momentum" on the basis that 0.045 exceeds −0.045 was effectively arbitrary, and is reported as such rather than presented as a data-driven finding.

### Headline — multifactor neutrality (Section 5)

| Metric | Value | Target |
|---|---|---|
| Beta to market (SPY) | −0.061 | ~0 |
| Correlation to market | −0.189 | ~0 |
| Max exposure to any factor | 0.071 | small |
| Multifactor R² (all 7) | 0.056 | low |
| Annualized alpha | −0.7% | positive |

**The multifactor hedge works.** Exposure to every factor in the basket is small, and no combination of the seven factors explains more than about 6% of the strategy's variance. This is the strongest form of the neutrality claim: the strategy is neutral not merely to the market, but simultaneously to size, value, momentum, and high-beta/low-volatility risk.

The neutrality is slightly less pristine than the earlier single-index result on TSLA (which reached R² of 0.0005). Two plausible reasons, both structural rather than errors: the hedge is estimated at entry and frozen for the duration of a trade, so exposures drift during long holds; and COST's returns are more factor-driven than TSLA's, so its residual is a smaller share of total variance, making any hedge error a proportionally larger contaminant.

### Risk-adjusted performance (Section 5)

179 trades; final equity **$85,234** from $100,000; in a position 57.4% of days.

| Metric | Value |
|---|---|
| Sharpe ratio | −0.231 |
| Sortino ratio | −0.238 |
| Annualized volatility | 5.8% |
| Max drawdown | −16.9% |
| Total return | −14.8% |
| CAGR | −1.5% |

The loss is not a hedge failure or a regime effect. It is the arithmetic consequence of trading a zero signal: with no edge to capture, 179 trades across a multi-leg basket accumulate transaction and borrow costs, and the equity curve bleeds accordingly.

### In-sample vs. out-of-sample (Section 6)

| Metric | In-Sample (2015–2021) | Out-of-Sample (2022–2025) |
|---|---|---|
| Sharpe | −0.168 | −0.378 |
| Total return | −7.5% | −7.1% |
| Max drawdown | −16.4% | −10.2% |
| Beta to market | −0.087 | 0.000 |
| Max abs factor beta | 0.097 | 0.087 |
| Annualized alpha | −0.04% | −2.0% |
| Number of trades | 109 | 47 |

Two things to read here, and they point in opposite directions.

**The neutrality holds out-of-sample.** Market beta is 0.000 and the maximum factor exposure is 0.087 on data the hedge never influenced. The hedging machinery is robust — this is the reliable, reproducible part of the result.

**There was never any alpha to survive.** Unlike the earlier TSLA stat-arb strategy — where in-sample performance looked mildly positive and then decayed — here the in-sample Sharpe was already negative (−0.168). The signal did not degrade out-of-sample; it never worked at all. That is a cleaner and more conclusive negative result than a decay would have been, because it removes regime change as an explanation.

### What this establishes

Read alongside the two earlier strategies, this is a controlled experiment rather than a third attempt. Each iteration removed a specific confound:

- **Momentum on TSLA:** an edge that hinged on a single trade and decayed out-of-sample.
- **Single-index stat-arb on TSLA:** market exposure hedged away and neutrality proven; the residual-momentum signal was still weak (gross Sharpe 0.139). *Objection: perhaps TSLA is a pathological, options-dominated name, and perhaps a single-index hedge is too crude.*
- **PCA multifactor on COST (this strategy):** both objections addressed — a clean, fundamentals-driven, moderate-weight stock, and a proper multifactor hedge. The signal is not merely weak but zero (gross Sharpe 0.045).

The conclusion the evidence supports: **monthly-horizon residual momentum on individual large-cap US equities does not carry a tradeable edge, and this holds regardless of the choice of stock or the sophistication of the hedge.** The framework is sound, its neutrality is demonstrated and robust out-of-sample, and the honest finding is a negative one — which is what rigorous testing exists to produce.

![clipboard.png](../../../../../../private/var/folders/64/8c76lfjs7kq52sph54q_1bwc0000gn/T/clipboard.png)

## Limitations and next steps

The results reprioritize these — the signal, not the hedge, is now clearly the binding constraint.

- **The signal needs replacing, not tuning.** Residual momentum at a monthly horizon is empirically zero on this name (gross Sharpe 0.045). Re-tuning its windows or thresholds against this same data would be curve-fitting, not improvement. A genuinely different hypothesis with its own economic basis is required — for example, *short-horizon* residual reversal (large one- to two-day idiosyncratic moves in liquid names often partially reverse, driven by transient liquidity demand rather than information), or a signal built from data outside the price series entirely, such as sentiment or earnings revisions.
- **Turnover is punishing at this signal strength.** 353 signal changes and 179 trades across a multi-leg basket means costs dominate whenever the edge is small. Any future signal must clear a materially higher bar than "positive gross Sharpe" — it must be strong enough to survive the cost of trading a hedged basket. A wider entry threshold or a longer minimum holding period would reduce turnover, but only makes sense once a real edge exists.
- **Cross-sectional application is the natural extension.** The framework trades one stock's idiosyncratic return, which is inherently noisy. Applying it across a cross-section of names — trading a diversified portfolio of residual signals — would average out much of that idiosyncratic noise. This is how real market-neutral books are constructed, and it is the single most promising structural improvement.
- **Hedge frozen during a trade.** The PCA hedge is estimated at entry and held through the position, so exposures drift during long holds. This likely explains part of why neutrality here (R² 0.056) is slightly less pristine than the single-index result. Refreshing the hedge intra-trade (e.g. weekly) would tighten it at the cost of turnover.
- **Fixed factor count.** The component count is set by a variance threshold with a floor of three, which binds most of the time (3.2 average). A more careful treatment would test the sensitivity of the residual to this choice.
- **Walk-forward validation.** A single train/test split is one comparison. Rolling walk-forward re-estimation across many windows would give a more robust read — though with a gross Sharpe of 0.045, there is currently no edge for it to validate.
