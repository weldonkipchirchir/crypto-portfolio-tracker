# Liquidation scenario heatmap

Browser-only hypothetical isolated linear USD-contract scenario calculator. No subscription, API, account access, or market-data feed is needed. This is not CoinGlass data and never infers actual positions from an order book. Initial view has no modeled positions; the example button explicitly loads example assumptions for review before calculation.

Users specify an uppercase scenario symbol (label only, no claimed venue coverage), entry/reference price, total entry notional, long allocation, distinct leverage buckets, and optionally maintenance percentage (empty means explicitly documented 0%). Each side is allocated equally across leverage buckets. Prices assume a common entry for all positions. Cell intensity encodes assumed entry notional relative to the largest cell in the current scenario. It is neither actual liquidity nor probability and is not comparable across separately normalized scenarios.

For quantity q, entry E, leverage L, and maintenance fraction m, initial collateral is qE/L. Solve collateral plus linear unrealized PnL equals qPm: long P = E(1−1/L)/(1−m); short P = E(1+1/L)/(1+m). Require m < 1/L to start above maintenance. At L=1 a long reaches zero in the simplified model. Zero allocations are shown as inactive. Leverage bounds 1–200 are calculator limits, not venue availability.

Excluded: fees, funding, tiers, maintenance deductions, added margin, cross/portfolio margin, inverse contracts, and exchange liquidation procedures. Real triggers depend on mark prices and venue rules. Primary reference reviewed 2026-11-04: [Bybit liquidation process](https://www.bybit.com/en/help-center/article/UTA-Trading-Rules-Liquidation-Process). This implementation derives the simplified zero-fee, zero-deduction constant-rate equation; it does not reproduce a live venue calculator.

Run `node --test feature_liquidation_heatmap.test.cjs`. Tests verify the equity equation, leverage monotonicity, allocation conservation, invalid input rejection, safe escaping, empty initial state, and no API calls. Module exports through `OrbitFeatureModules.liquidation_heatmap`; no shared integration files edited.
