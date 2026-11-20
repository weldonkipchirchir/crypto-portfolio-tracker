# Research-led Insights release

## Implemented
- Observed wallet-value checkpoints saved explicitly by the user, with a real timeline and 7/30-day filters. No points are backfilled. A single checkpoint does not become a fabricated historical chart. Checkpoints persist on the account, keep exact Decimal strings, and record stale/unpriced counts plus wallet membership and balance fingerprints.
- Contract-based favorites for currently held assets, grouped across wallets on the same chain. Token symbols alone never merge two assets. Favorites are saved on the account and remain removable if the holding disappears.
- An asset research dialog with exact aggregated quantities, per-wallet balances, canonical contract/mint, source and observation times, selected-pool liquidity and optional 24-hour pool price movement/volume. Market movement is separate from personal P&L.
- Account isolation, bounded records (365 checkpoints, 50 favorites), one checkpoint per minute, authenticated server-authoritative calculations and transaction locks. SQLite and PostgreSQL tests exercise the endpoints.

Checkpoint value change can include deposits, withdrawals, balance changes, added/removed wallets, discovery coverage and stale quotes. It is not investment return, tax profit or cost basis. Existing wallet and trade holdings remain separate. Refresh balances/quotes before saving a checkpoint when current observations are needed. Partial coverage is explicit, not a health or safety score.

## Research references
- CoinStats Time Machine: https://help.coinstats.app/en/articles/16861043-portfolio-time-machine-overview-and-how-it-works
- CoinStats custom alerts: https://help.coinstats.app/en/articles/3573865-how-to-set-up-custom-alerts
- CoinMarketCap portfolio: https://support.coinmarketcap.com/hc/en-us/articles/27634136792859-What-is-the-CMC-Portfolio
- CoinMarketCap feature overview: https://coinmarketcap.com/academy/article/coinmarketcap-features-track-research-and-build-with-crypto-data
- DEX Screener API: https://docs.dexscreener.com/api/reference

These references inform workflow and data distinctions; Orbit does not claim feature parity, affiliation or identical provider coverage.

## Recommended next work
Contract-linked purchase-cost records and reconciliation; refresh-evaluated price targets with an in-app inbox; scheduled monitoring only after durable jobs and delivery/retry infrastructure exist. Exchange API integrations, tax reporting, DeFi position decoding and historical reconstruction each require separate provider and accounting validation. They are not silently implied by the Insights UI.

## Validation
Run `python -m unittest discover -q`, `node test_ui.cjs`, and `node advanced_dashboard.test.cjs`. Real PostgreSQL tests use ORBIT_TEST_DATABASE_URL against a disposable database with per-test schemas. Browser QA checks favorites, persisted observations, research-dialog identity, filters, privacy, and narrow layouts before updating production.
