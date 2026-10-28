# Orbit crypto portfolio tracker

Separate workspace: D:\crypto-portfolio-tracker

Run with Python 3.12+: `python server.py`, then open http://127.0.0.1:8042.
Run accounting checks with `python -m unittest -v`.

Working features: private local user accounts, password hashing, expiring HttpOnly sessions, per-user SQLite storage, manual trades, atomic CSV imports, CSV export, weighted average buy/sell prices, fee-adjusted realized P&L, manual current valuations and unrealized P&L, public address watchlists.

CSV columns: date,symbol,side,quantity,price,fee,account. Date is ISO 8601 (naive timestamps are UTC); prices/fees are USD. Import purchases before sales. Identical file reimports are rejected; overlapping exports can still create duplicates. Transfer history is not imported; do not enter transfers as buys/sells.

Integration status: live native coin balance adapters for Ethereum, Optimism, BNB Chain, Solana, Aptos and Sui (GraphQL). Click Sync balances in Connections. Read-only browser EVM wallet connection is available when an injected wallet provider is present; otherwise add public addresses. Coverage varies by chain; see NETWORKS.md. Binance read-only Spot balance connections are available when server encryption is configured; staking and Robinhood brokerage syncing are not included. Never provide seed phrases or private keys.

Market prices: click Prices to fetch supported USD quotes from CoinGecko (BTC, ETH, SOL, BNB, APT, SUI, OP, USDC and USDT). Quotes show provider timestamps and stale status after 15 minutes. Manual prices are supported. Public endpoints can rate-limit; errors are shown and last successful balances are retained. Identical CSV files are rejected; overlapping files still require reconciliation.

Optional environment variables: COINGECKO_DEMO_API_KEY, ETH_RPC_URL, OP_RPC_URL, BNB_RPC_URL, SOL_RPC_URL, APT_RPC_URL (full /v1/view URL), SUI_GRAPHQL_URL. Set these in the process environment before launching. No keys are stored in browser storage. Wallet balances are displayed separately from trade holdings to avoid double counting. Native balances alone do not establish purchase cost basis.

Local development only. Before a public launch: deploy behind HTTPS, add login throttling and recovery, validated chain address adapters and historical indexing, encrypted exchange API credentials, transfer matching and deduplication, automated prices with timestamps, database migrations/backups and operational monitoring. The server binds to loopback. Do not expose this development server directly to the internet.

Accounting uses portfolio-wide weighted average cost (purchase fees included). Average buy/sell displayed prices exclude fees. This is performance tracking, not a jurisdiction-specific tax report. Asset identity currently uses symbols; chain/contract identifiers are needed before importing live tokens with ambiguous symbols.


## Deep review update (2026-10-24)

- CSV preview validates every row and accounting before save. Exact normalized duplicate rows in overlapping files are skipped; genuinely identical fills require review.
- Connections can inspect explicit ERC-20 contracts (max 20) and automatically enumerate Solana SPL/Token-2022 accounts. Quantities retain exact decimal strings and contract/mint identity; unverified tokens are not assigned dollar values or cost bases.
- Solana inspection shows the latest 25 finalized activity records, not classified trades or complete history.
- Trade filters include side, asset/account, UTC date range and gross/fee totals. Wallet native totals remain separate from the trade ledger.
- Request origins/hosts, JSON contracts, auth rate limits, strict script CSP, bounded workers and outbound request quotas are enforced. See SECURITY.md for the threat model and unresolved public launch requirements.
- All development tests use temporary databases. Run `python -m unittest discover -v`.
- Exchange credential setup and full historical ingestion remain pending; see INTEGRATIONS.md for official API research and prerequisites.


## Automatic Ethereum history

Adding an Ethereum address now fetches external native transactions and ERC-20 transfers into Transactions > On-chain history. Previously saved addresses fetch on first load if no history status exists. Data is persisted and deduplicated by chain event identity. Load older activity follows provider pagination (50 per stream/page). Refresh updates the newest page without deleting older saved records. Internal transfers, NFTs and decoded swaps remain outside this coverage. Transfers are not added to the P&L trade ledger without purchase-cost information. Provider failures preserve previously fetched history.


## Swap detection and cost-basis review

Review groups confirmed history by wallet, chain and transaction; it nets each asset by chain/contract identity. One sent asset plus one received asset is a suggested swap, not a verified trade. Incoming assets can be reviewed to record a verified original acquisition; transfers and failed/pending transactions are never automatically purchases. Complex movements require manual review.

Confirmation requires actual date, total USD value, fees and identity acknowledgment. Swap sale and purchase are committed together after holdings validation; missing source purchases block confirmation. Review IDs remain stable across additional history pages and cannot be confirmed twice. Dismissal adds no trades. Arbitrary token contracts use separate ledger aliases; native/market symbols are reserved to avoid pricing counterfeit tokens as genuine assets. Exact quantities are read from saved history rather than client input. Fees are entered in USD; native gas units are shown as context and are not converted using today's price. Full internal/DeFi/bridge decoding remains outside current coverage.


## Other-network history (25 October 2026)

History dispatch now covers Ethereum, Optimism, BNB Chain, Solana, Aptos and Sui. See NETWORKS.md for exact support, provider configuration and limitations. BNB history requires a server-side Etherscan V2 API key; balances do not. Optimism native trades use ETH_OP so chain identities do not collide. Sui unknown-decimal tokens retain raw units and block review for their entire transaction. Older saved histories are refreshed once after this upgrade.


## Base, Arbitrum, Polygon and Avalanche

Added four mainnet options with native balances, explicit ERC-20 inspection, wallet chain selection, USD quotes and distinct review ledger identities (ETH_BASE, ETH_ARB, POL, AVAX). Avalanche C-Chain has public native history; Base/Arbitrum/Polygon indexed history needs configured Etherscan access, with a paid plan for Base. See NETWORKS.md for exact limits.


## Sonic, Gnosis and Celo

The tracker now lists 13 networks. Sonic (S), Gnosis (XDAI) and Celo (CELO) support balances, market quotes, ERC-20 inspection, browser-wallet network selection and separate ledger aliases. Gnosis/Celo have public external transaction and token-transfer history. Sonic native history needs Etherscan API access. Celo alternate gas currencies are not normalized automatically. Details and provider limits are in NETWORKS.md.


## Bitcoin, Stellar, TRON and new EVM mainnets

Added Bitcoin, Stellar, Tron, Circle Arc mainnet, Monad mainnet, Robinhood Chain mainnet and Linea:20network choices. BTC/Stellar/TRX have dedicated checksum-aware native balance/history adapters; four EVM chains have native balances/ERC-20 inspection and configured explorer-history adapters. Arc native USDC/interface quantities are kept separate from arithmetic to avoid duplicate holdings. Robinhood Chain is independent of exchange/broker account imports. See NETWORKS.md for exact coverage, keys and unsupported operations.


## Automatic token holdings and PONS

Wallets now keep persisted token snapshots and watched ERC-20 contracts. Global Sync refreshes native balances, market prices and token holdings sequentially; new wallets trigger token checks automatically. Manual inspection persists contract choices. Names/symbols are read via bounded ERC-20 ABI decoding and treated as unverified metadata. Amounts retain exact decimal strings. Partial/provider failures retain clearly marked stale last-known values; zero balances replace previously positive values.

For EVM discovery, configure a compatible Alchemy token-indexer endpoint via the per-chain environment variable in token_discovery.ENV_NAMES (for example ALCHEMY_RH_RPC_URL for Robinhood Chain). Supported indexer coverage varies. Without that, ETHERSCAN_API_KEY can discover contracts from up to100 recent token transfers (not a complete holdings inventory). Without credentials, Robinhood Chain checks a limited PONS catalog; other EVM networks show that broader indexing is unavailable. At most20 contracts are queried per refresh. The app does not promise exhaustive token discovery, prices or purchase history.

The Robinhood Chain PONS contract is0x39dbed3a2bd333467115de45665cc57f813c4571. It is distinct from the public holder wallet address. Native ETH can be zero while PONS holdings are positive. Token metadata/balances were read directly from the chain; PONS USD valuations are not inferred from its ticker. Never enter this token contract as a replacement for the wallet holding it.

### Token USD values
Token holdings display indicative USD unit prices and values from DEX Screener, matched by network and contract address. Quotes use the highest-liquidity eligible pool with at least $10,000 reported liquidity, cache for 60 seconds, and show their observation time. Unsupported or unquoted tokens remain Unpriced; retained older quotes are marked stale. Refresh Prices updates saved token valuations. Market value does not establish purchase cost or profit/loss. Partial token discovery means wallet totals can be incomplete.

## GitHub / Vercel
Full hosted deployment uses the included Python function and PostgreSQL adapter; see DEPLOYMENT.md for required environment variables, owner registration restriction and preview validation. Local SQLite remains the default when DATABASE_URL is absent. Local financial records are never bundled for deployment.

## Research-led Insights
Insights adds account-saved wallet-value checkpoints, a contract-based holdings watchlist and an asset research dialog with selected-pool liquidity, volume and 24-hour movement. The chart starts from real saved observations; its change is not investment return. See ADVANCED_FEATURES.md for scope, research references, storage bounds and validation. Run `node advanced_dashboard.test.cjs` alongside existing checks.

## USD price targets
Targets adds recurring inclusive price conditions and an account event history, evaluated on explicit price refresh or target creation. It uses fresh provider quotes and exact contract identities; it does not monitor in the background or send email/push. See PRICE_TARGETS.md for research, limits and validation.

## Top-ranked coin markets
Markets loads up to 250 CoinGecko market-cap-ranked coins with search, sorting and pagination. Coin pages include real historical USD charts, supply, cap/FDV, volume and exact-ID-matched DefiLlama protocol revenue. Unlock summaries require an existing DEFILLAMA_API_KEY API subscription; missing schedules are never inferred from supply. See MARKETS.md for provider setup, provenance, caching and limits.


Market research: see [RESEARCH.md](RESEARCH.md) for sentiment, narratives, RSI, exchange structure, funding/open interest, watchlists and recorded trade overlays, including public-feed coverage limits.


### Chart studies and Dashboard v7

Chart Studio has 41 curated study choices and individual × controls in the indicator legend. Removing a built-in study updates its saved configuration. Removing one custom plot is retained on interval reload and setup restore; applying its source again resets those per-plot removals. Drawings are independent.

The exact supplied Combo Dashboard v7 (Scored Signals) source can apply an explicitly labeled Orbit-native default-filter preset. A toolbar/library entry provides the same preset. It shows EMA trend, previous-closed-higher-timeframe trend, ADX/DMI, volume average, Bollinger-width percentile and five-check scores. Higher-timeframe candles come from a separate same-source request and never use a bar that closes after the current chart-bar timestamp. Monthly HTF is unavailable. Missing data prevents an eligibility verdict. EMA initialization follows Orbit’s loaded-history/Pine subset behavior; short histories remain seed-dependent.

This is not general Pine execution. Edited versions use the normal supported subset. The preset does not run the supplied MACD/dip signal triggers, last-direction/cooldown state, stop/target labels, VWAP plot, shapes, Pine alerts or strategy orders. Missing volume is treated conservatively as unknown rather than passing the original script’s missing-volume condition. These limitations are visible in the UI. Source attribution and MPL 2.0 notice are retained in combo_dashboard.js and fixtures/combo-dashboard-v7-scored.pine.


Chart Studio visibility and colors: each active study has an eye button, a color picker and a separate remove button. Hidden studies remain in the setup but stop drawing and influencing its price scale. Visibility and selected colors persist with account setups. Default colors are distinct across active native and custom studies; hovering a plotted study highlights its matching name. See [EXCHANGE_SECURITY.md](EXCHANGE_SECURITY.md) for Binance scope, AES-256-GCM storage, credential permission checks, Secret custody and key rotation. Exchange Spot balances are displayed separately on Overview; no purchase costs are inferred.


Overview and Connections now share a combined connected-value summary (wallets + exchange balances), separate recorded-trade valuations, and a persistent Hide assets below $1 preference. Unknown prices stay visible and filtered assets remain in totals. Wallet/address identities and verified Binance account fingerprints are deduplicated in the combined summary. Legacy duplicate exchange connections without fingerprints require a balance sync before they can be recognized. 15m and 1H quick candle selectors are available beside 4H/1D/1W.

Automatic portfolio pricing checks every five minutes while authenticated and visible, with an initial check after opening, no overlapping polls, and a ten-minute backoff on failures. It pauses behind open dialogs and while editing fields. Auto prices can be paused; Refresh prices runs a manual check. Binance snapshot revaluation uses stored quantities and public cached market quotes; it does not decrypt API credentials or refresh balances. Balance timestamps stay unchanged. CoinGecko market-list caching is up to five minutes; unsupported assets retain a stale saved valuation or remain unpriced. Balance sync remains explicit.


Performance overview: colored 24h/7d/30d provider changes plus on-demand 90d history, a searchable connected/recorded holdings explorer, recorded average buy and fee-inclusive remaining entry cost, realized/unrealized P&L cards and an annual realized-trade calendar. Market movement reconstructs earlier values for current quantities and reports covered exposure; it is not portfolio investment return. 90d is derived from a genuine 89–91-day provider window, checked against recent observation times, never substituted with a 200d percentage. History loads progressively with stop/retry behavior and cached completed coins.

The yearly calendar covers all recorded sale years and includes UTC sale-day profits/losses using the same weighted-average cost and fee policy as the ledger. No-sale days stay distinct from break-even sale days. No historical unrealized P&L is inferred from current balances. Coin details keep connected cost basis unlinked, preserve contract identity, show available market cap/supply data, and link verified IDs to Markets; unknown assets use a search rather than a guessed ticker match. Legacy allocation, balance and accounting sections are collapsed for readability.

Binance sync queries both Simple Earn Flexible and Locked positions independently of Spot receipts. Verified underlying amounts are displayed without double counting LD receipt balances. Unpriced positions are hidden from the main holdings explorer and exchange tables; they are retained in snapshots. Private Alpha account balances are not supported by this connector. After upgrading, use **Connections → Sync balances** to fetch newly supported Earn positions.

The overview includes a two-step beginner checklist, contextual terminology examples, direct Connections/import/trade shortcuts and plain-language realized/unrealized profit labels. Help can be collapsed; its open state survives portfolio price rerenders during the session. Trading records are still required for profit calculations.

Chart UX: phone charts fit their price/date axes into the available width, use a taller plot and begin with up to 45 candles (120 on desktop). Zoom-out/reset reveal additional loaded observations. Candle size and history range remain separate. Data-source/timezone settings and advanced Studio drawing controls are expandable; a chart-reading guide explains candles and indicators. Studio interval, drawing and indicator strips scroll independently on small screens.

Reliability: the overview reports per-connection balance sync timestamps and incomplete Flexible/Locked Earn coverage. A 15-minute review threshold is a UI prompt, not evidence of a failed sync. Holdings CSV exports use the active source/search/account/dust filters across all pages, omit credentials and preserve exact quantity strings. Unknown values remain excluded. API reads time out after 30 seconds and save/sync requests after 90; writes are never automatically retried, and users are told to verify uncertain saves before resubmitting.

Studio groups candle duration separately from the selectable history range, with independent Candles/Line controls. The selected duration has a check mark and high-contrast light/dark colors. Changing history reloads the current duration through the existing provider adapter; zoom only changes the visible portion of loaded data. Provider coverage limits still apply.

CSV import recognizes Binance Spot Order History exports with duplicated Time columns and superscript headers. Only FILLED orders are normalized, using the final execution Time, Executed base quantity and Average Price. Preview accepts an explicit UTC offset and USD-per-USDT rate (one rate per file); USDT parity is an acknowledged estimate, not verified historical conversion. Fees are absent in this export and recorded as zero with an explicit acknowledgement required by the server before saving. Unsupported quote currencies are rejected. Orbit CSV format remains supported. Exports of individual trade fills and canceled/partially filled orders are not yet supported by this adapter.
