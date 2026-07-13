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

*(Complete this section after running `notebooks/05_pca_multifactor_statarb.ipynb` against live data. The numbers below are placeholders — fill them from Sections 2, 3, 5, and 6 of the notebook.)*

**Hedge diagnostics (Section 2):** principal components used ≈ **[fill in]** on average; the replicating hedge basket's average weights were **[fill in]**.

**Direction test (Section 3):** momentum gross Sharpe **[fill in]** vs. reversal gross Sharpe **[fill in]** → chose **[momentum / reversal]**.

**Headline — multifactor neutrality (Section 5):**

| Metric | Value | Target |
|---|---|---|
| Beta to market (SPY) | **[fill in]** | ~0 |
| Correlation to market | **[fill in]** | ~0 |
| Max exposure to any factor | **[fill in]** | small |
| Multifactor R² (all 7) | **[fill in]** | low |
| Annualized alpha | **[fill in]** | positive |

**Risk-adjusted performance (Section 5):** Sharpe **[fill in]**, Sortino **[fill in]**, annualized volatility **[fill in]**, max drawdown **[fill in]**.

**In-sample vs. out-of-sample (Section 6):** **[Did neutrality hold across factors out-of-sample? Did the alpha survive or decay? State it plainly. Neutrality that holds out-of-sample is the strong, reliable result; alpha that decays is an honest finding worth reporting.]**

*[Insert the equity curve chart from the notebook here.]*

## What to say about this in an interview

- **Lead with the multifactor neutrality.** "I hedge the stock against the principal components of a diversified factor basket, so it's neutral not just to the market but to size, value, momentum, and high-beta risk simultaneously. I prove it: the maximum exposure to any single factor is [X], and the multifactor R² is [Y]." That is a materially stronger claim than single-index neutrality.
- **Explain why PCA rather than raw multiple regression.** "The hedge ETFs are collinear, so regressing on them directly gives unstable betas. PCA extracts orthogonal factors, which makes the hedge stable — it's principal component regression."
- **Justify the design choices.** The stock was chosen for structural reasons (trended up, fundamentals-driven, moderate index weight, not options-dominated like TSLA); sector ETFs were excluded to avoid self-hedging. Being able to defend these choices demonstrates real understanding.
- **Be honest about the signal.** If the residual-momentum signal is still weak or fails out-of-sample, say so — and note that the framework's value is the clean multifactor hedge, into which a stronger signal (sentiment, a learned feature set) could be plugged.

## Limitations and next steps

- **Hedge frozen during a trade.** The PCA hedge is estimated at entry and held through the position; factor exposures drift between rebalances, so neutrality degrades slightly during long holds. Refreshing the hedge intra-trade (e.g., weekly) would tighten it at the cost of turnover.
- **Signal strength.** The residual-momentum signal is the same one that was weak on TSLA; a cleaner residual gives it a better chance, but the signal itself may still need replacing with something with a stronger economic basis.
- **Fixed factor count.** The number of principal components is chosen by a variance threshold with a floor; a more careful approach would test the sensitivity of results to this choice.
- **Single stock.** The framework is demonstrated on one name. Applying it across a cross-section of stocks — trading a portfolio of idiosyncratic signals — would diversify the idiosyncratic risk and is the natural next step toward a real market-neutral book.
- **Walk-forward validation.** A single train/test split is one comparison; rolling walk-forward re-estimation across many windows would give a more robust read on whether any edge persists.
