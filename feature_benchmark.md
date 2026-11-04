# Portfolio benchmarks

`feature_benchmark.js` registers `OrbitFeatureModules.benchmark` in the existing workspace. No database writes, new backend routes or cash-flow assumptions are introduced.

The tool reads saved `historical_portfolio` observations, then requests bounded 365-day CoinGecko BTC and ETH line histories through the existing market-chart API. Empty saved history skips market requests. Provider errors show unavailable comparisons.

For the selected source, the latest sample per UTC date is retained. Only UTC dates present in all three series are compared, with a shared opening date and index of 100. The calendar window ends at the latest common date. Intraday observations are not synchronized: exact timestamps appear in the table. Missing dates are not interpolated, and lines break at gaps and flagged coverage observations. Connected holdings and wallet checkpoints are never combined. Zero opening portfolio value leaves its index unavailable.

Observed portfolio value changes include deposits, withdrawals, balances, coverage and account membership changes. They are not investment returns. Recorded buys/sells do not establish external deposits/withdrawals. The tool deliberately leaves investment return and investment outperformance unavailable until a complete verified external-flow ledger and reliable valuation boundaries exist. BTC/ETH show USD price changes excluding fees; the portfolio curve is neither a historical holdings reconstruction nor a hypothetical constant-quantity strategy.

Validation: `node --test feature_benchmark.test.cjs` (6 tests), covering common dates, unknown/deposit flows, zero denominator, coverage flags, source isolation, bounded calendar selection and provider/empty-history states.

## Optional user-supplied Modified Dietz estimate

The browser-only form uses the first and last selected common-date saved portfolio values and their actual observation timestamps, never benchmark prices or trades as cash flows. Users must acknowledge complete statements for the selected source and consistent valuation coverage, even for zero external flows. No inputs or estimates are persisted. Editing input invalidates the displayed estimate; refresh and source/window changes clear inputs.

Enter at most 500 lines of `UTC timestamp,signed USD`, e.g. `2026-10-02T12:00:00Z,+100`. Positive amounts are external deposits; negative amounts are external withdrawals across the exact selected source boundary. Internal transfers and trades are not inferred to be external flows. Opening observations already include flows at the opening timestamp; therefore accepted flows are strictly after opening and at or before closing, with closing values required to include flows at their timestamp.

The formula is `(closing - opening - sum(flows)) / (opening + sum(flow * (closingTime - flowTime)/(closingTime - openingTime)))`. The weighted-capital denominator must be finite and positive. Invalid dates, unknown/incomplete flow declarations, non-increasing timestamps and partial/stale/flagged valuation boundaries are rejected. Costs included in observed valuations are not subtracted again.

This is an unannualized user-supplied estimate, not verified return or exact TWR. Large flows during volatile markets can reduce accuracy. Method reference: [GIPS Standards Handbook for Firms, Modified Dietz discussion](https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/). The tool uses elapsed timestamp weights rather than an end-of-day convention and makes no claim of GIPS compliance. Existing `investmentReturn` remains null; the optional form does not alter the value-comparison series.

Validation now includes 11 passing tests with deposits, withdrawals, completeness, zero and negative capital, valid/invalid UTC dates and window boundaries, 500-flow limit, flagged endpoints, source isolation and form lifecycle.

Freshness provenance is required for both adjusted-return boundaries; legacy observations without verified freshness are rejected. Final benchmark suite: 12 passing tests.
