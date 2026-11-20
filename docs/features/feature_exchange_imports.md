# Exchange history and activity

Register `feature_exchange_imports.js` and route feature `exchange_imports` reads to `feature_exchange_imports.read(c, uid, raw)` under the existing provider budget. No init/action hooks, migrations or schema changes. Do not hold a database write transaction during the read. Credentials come only from the authenticated owner's saved read-only connection. Default read exposes connection IDs and labels only. Nothing runs automatically in the background.

## Spot fills

`operation: preview` accepts id, pair (USDT Spot only), from_id (decimal string starting at 0), and usdt_usd_rate. One fixed GET to Binance myTrades returns normalized CSV and a string next_from_id, preserving 64-bit IDs in the browser. One explicit fetch covers at most 1,000 fills. Existing authenticated import-preview/import endpoints handle review, duplicates and separately confirmed ledger writes.

Non-USDT commissions fail closed pending historical fee valuation. Conversion uses the supplied USDT/USD rate, not historical FX. Identical legitimate fill ledger values retain the existing normalizer's manual-review protection. Account identity matches the existing Binance API importer for overlap detection.

## Deposits, withdrawals and rewards

`operation: activity` accepts id, activity (`deposits`, `withdrawals`, `flexible_rewards`, `locked_rewards`), start_utc/end_utc (`YYYY-MM-DDTHH:MM`, explicitly UTC), and page (string 1–10; deposits/withdrawals require 1).

All activity dates must be within the last 90 days and end at or before now. Deposits and withdrawals require a window shorter than 90 days and return at most 1,000 records, offset 0 only. Narrow the date range if the page is full. Flexible and Locked rewards require a window of at most 30 days and return at most 100 records per explicit fetch. Reward pages 1–10 allow observing at most 1,000 records per account/activity/window. Page changes require another user fetch. Flexible requests type ALL. A short page does not guarantee complete exchange history.

Each request issues exactly one signed GET to one of four hardcoded Binance paths. No redirects, automatic retries, mass account queries, subscriptions, redemptions, orders or transfers. HTTP timeout is at most 10 seconds and respects the provider deadline; JSON body is capped at 2 MiB. API errors and permission failures use a generic local message, never raw upstream errors or credentials.

Normalized output contains activity, exact native asset symbol/amount, native withdrawal fee with fee asset, exchange status code and label, UTC time, txid, reference, reward type, and named source. Deposit fees and reward fees are blank when not supplied, not assumed zero. Deposit time uses insertTime; withdrawal time uses applyTime (UTC request time), not completion time. Rewards are read exclusively from reward history; Earn principal subscriptions/redemptions are excluded. Unknown numeric statuses remain explicitly unknown. Address and arbitrary extra upstream fields are not returned. JSON preserves exact values; CSV neutralizes spreadsheet formula prefixes in text fields.

Activity is an observed read-only timeline and downloadable normalized CSV. There is no activity persistence or trade import button. Its CSV intentionally has different headers from trade CSV and is not accepted as a trade import. Deposits are not automatically income; withdrawals are not automatically sales. No USD valuation, historical cost basis, realized profit/loss change or tax classification is inferred. Pending/rejected records are labeled rather than treated as successful balance changes. No new read/write permissions should be enabled if a read-only key cannot access a region's history.

## Official references checked

- Spot account trade list: https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/account#my-trades
- Deposit/withdrawal schemas and constraints: https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/capital
- Flexible/Locked reward schemas, 30-day windows and 100-row caps: https://developers.binance.com/en/docs/catalog/investment-and-services-simple-earn/api/rest-api/flexible-locked
- Official connector confirms methods and parameters: https://github.com/binance/binance-connector-python/blob/master/clients/simple_earn/src/binance_sdk_simple_earn/rest_api/api/flexible_locked_api.py

## Validation

`python -m unittest feature_exchange_imports_test`: 19 tests pass. Covers owner isolation before decrypt/network, large fill IDs, fee valuation, bad cursors, invalid/outside dates, page bounds, native numeric rejection, activity label semantics, field redaction, exact fees/rewards, fixed signed GET, one request, NoRedirect, body limit, permission error redaction and CSV formula safety.

`node feature_exchange_imports_ui_test.js`: activity labels and account label escaping pass. `node --check feature_exchange_imports.js`: passes. Live exchange calls and full browser integration were not run; tests use mocked responses and no user credentials.
