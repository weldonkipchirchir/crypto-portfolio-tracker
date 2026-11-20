# Funding history

Read-only Binance USDⓈ-M and Bybit linear USDT perpetual settlements for an exact curated `exchange_charts.ASSETS` identity (Bitcoin default). Public endpoints use no exchange credentials.

Official references checked November 4, 2026:
- https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History (`GET /fapi/v1/fundingRate`, milliseconds, maximum 1000 rows)
- https://bybit-exchange.github.io/docs/v5/market/history-fund-rate (`GET /v5/market/funding/history`, linear category, milliseconds, maximum 200 rows)

Each request supplies start and end for the last 30 days. One request per venue; a full response is explicitly marked truncated, never represented as complete history. Invalid/future/out-of-window/nonfinite records are omitted. Errors preserve the other venue. Cache is five minutes, keyed only by validated identities and bounded by the curated mapping size. No database or account data is read.

Rates are fractional rates converted to percent per settlement. The APIs do not provide historical contractual intervals here: the UI reports only elapsed hours between adjacent returned records on each venue, first unknown, explicitly warns that gaps may represent missing data, and does not annualize. Scatter observations do not interpolate or imply synchronized venue timestamps. A semantic table exposes UTC timestamps and interval units.

A browser-only notional scenario replays returned historical rates at constant USDT notional, with positive long cost / short receipt and a clear hypothetical label. It excludes trading P&L, fees and missing data; it is not a forecast or personal funding payment report.

Validation: `python -m unittest feature_funding_history_test`; `node --test feature_funding_history.test.cjs`.
