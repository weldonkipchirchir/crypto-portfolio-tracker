# Orbit implementation and security review

Reviewed on 24 October 2026 with three parallel agents covering security, integration research, and portfolio UX. Changes live in D:\crypto-portfolio-tracker; the event-flow application is separate.

## Working capabilities

- Local private accounts, separate trade ledgers, public wallet address tracking, USD valuations and weighted-average realized/unrealized P&L.
- Native balances for Ethereum, Optimism, BNB Chain, Solana, Aptos and Sui.
- ERC-20 balances for up to 20 specified contracts on the three EVM networks. Solana legacy SPL and Token-2022 account enumeration, aggregated by mint.
- Most recent 25 finalized Solana activity records. This is metadata, not decoded swaps, buys or sales, and is not complete historical coverage.
- CSV preview with per-row errors, accounting validation, duplicate detection across overlapping exports and atomic writes.
- Filters by asset/account, buy/sell side and UTC dates, with gross amounts and fee totals.
- Separate native-wallet totals with partial coverage indicators, avoiding double counting alongside trade holdings.

## Findings addressed

| Finding | Change |
|---|---|
| Unbounded login requests and input sizes | Per-IP authentication limits; bounded bodies, email/password and numeric values |
| Cross-site localhost requests and DNS rebinding | Host allowlist, JSON-only mutations, matching Origin and Fetch Metadata checks |
| Weak browser script policy | External JavaScript; script-src self; removed inline event attributes; HTML escaping retained |
| Unbounded server/provider concurrency | 24 HTTP workers, overload responses, six concurrent provider operations, per-account request quotas and non-overlap |
| Oversized or slow provider responses | Response-size cap and outbound time budgets |
| Partial sync errors lose useful state | Preserve last successful balance and show provider error |
| Overlapping CSVs silently duplicate trades | Normalized row comparison and explicit preview counts/warnings |
| Concurrent sells can overdraw a holding | Immediate SQLite write transaction before ledger reads and validation; concurrent-sale regression |
| Logout response leaves a cookie | Session revocation plus cookie expiration; commit before sign-in response |
| User-entered account labels can become spreadsheet formulas | Export prefixes risky account labels; HTML views escape strings |

## Limits that remain

The app is suitable for local development. A public launch still needs production HTTPS hosting, durable rate limiting, verified email/password recovery or passkeys, account deletion and privacy controls, encrypted backups with restore checks, operational auditing and independent assessment. Process-local limits reset after restart. Styles still permit inline attributes.

Exchange API credentials are not stored and authenticated exchange connectors are not enabled. Robinhood and Coinbase research is in INTEGRATIONS.md. Encrypted credential storage and read-only permission verification must precede those connectors.

Full historical ingestion, transfer matching, bridge handling, staking/DeFi interpretation and tax reporting remain outstanding. Native balances and recent activity do not supply cost basis. Manually recorded trades are currently keyed by symbol; chain/contract identity must be added to the trade ledger before importing arbitrary on-chain tokens. Unverified inspected tokens do not get fabricated prices or P&L.

Exact duplicate import detection is intentionally conservative. Two genuinely identical fills with the same timestamp, asset, side, quantity, price, fee and account require review; the preview explains this limitation.

## Verification

Run `python -m unittest discover -v` for accounting, endpoint ownership, malformed requests, security headers, throttling, overload, token units, import atomicity and concurrent-sale tests. Fixtures use temporary databases. JavaScript is checked with `node --check app.js`; rendered navigation and dialogs were checked in the local browser without querying customer wallet addresses or changing portfolio records.

Official source links and exchange prerequisites: INTEGRATIONS.md. Threat model and deployment configuration: SECURITY.md.
