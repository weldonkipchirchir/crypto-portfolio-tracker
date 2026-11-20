# Period P&L explorer

`feature_period_pnl.js` registers `OrbitFeatureModules.period_pnl`. It reads the existing authenticated `state` API; no new backend endpoint, database tables or external quote requests are needed.

Today, month-to-date, year-to-date and inclusive custom dates use UTC. Offset-bearing timestamps are normalized to UTC; timestamps without offsets follow the ledger's UTC convention. The chart switches between daily known realized P&L and cumulative known realized P&L on sale dates. The table groups sales by the ledger symbol. Purchase history outside the selection remains included through the server's existing weighted-average `realized_pnl`; buy fees are capitalized and sale fees deducted there. Displayed sale fees are informational and are not subtracted again.

Missing calculated realized values invalidate the displayed total; known chart subtotals are explicitly labeled. Missing fee amounts remain unavailable. Empty recorded sales produce zero recorded realized P&L, which does not establish complete account coverage. Amounts use existing API floating-point output and USD display rounding, not tax reporting precision. Asset identity and accounting scope follow the existing symbol-based ledger; account-specific tax lots are not reconstructed.

Opening unrealized, closing unrealized, unrealized period change and total period P&L are explicitly unavailable. Existing `portfolio_calendar` snapshots contain connected balances and valuations, not matching historical ledger cost bases. Their differences can include cash flows and cannot establish unrealized P&L. Current unrealized values and wallet balance changes are never substituted.

Run `node --test feature_period_pnl.test.cjs`. Tests cover inclusive dates, UTC offsets, leap/invalid date validation, missing history, escaped symbols, and actual server weighted-average realized values including purchase and sale fees.
