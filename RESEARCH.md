# Market research workspace

## Available views
- Alternative.me Bitcoin-oriented Fear & Greed Index, including its real daily history and linked attribution.
- CoinMarketCap's official 90-day Altcoin Season Index through its documented keyless public endpoint. If unavailable, Orbit separately labels its own 30-day breadth calculation rather than presenting it as the same index.
- Seven CoinGecko narrative categories: RWA, AI, DeFi, gaming, memes, Layer 1 and Layer 2. Lists have local search and pagination. Categories overlap and may include tokens with different kinds of exposure; they are a discovery taxonomy, not endorsements.
- An account-saved market watchlist, independent of wallet-held favorites. Up to100 CoinGecko coin IDs; each user's records are private. Removed or no-longer-listed identities remain removable.
- Up to30 exchange pairs from the first100 CoinGecko tickers, with reported USD volume, spread, observation time and safe exchange links. This is partial listing coverage.
- Eight-asset daily Wilder RSI(14) heatmap. It requires consecutive completed UTC daily closes, rejects stale or incomplete candles, and labels the actual venue/pair. Binance USDT candles have a Coinbase USD fallback. Overbought >=70 / oversold <=30 are indicator bands, not trade instructions.
- Binance public spot order-book depth (top100 bid/ask levels) and large executed prints (>=100,000 USDT within the latest100-trade sample). Refresh is manual; open orders can be cancelled. These prints are not verified whale wallets, a complete history or background alerts.
- Binance, Bybit and OKX long/short account ratios. They measure account counts rather than position notional. OKX's currency-wide contract scope is shown separately from an individual USDT perpetual.
- Public funding and open-interest snapshots for Binance, Bybit and OKX. Funding is a signed fraction per provider period, not an annualized return. Base-asset quantities, contract counts, USDT quote values and provider-reported USD values are kept distinct; no cross-venue aggregation or USDT-to-USD conversion is invented.

## Recorded buy/sell chart overlay
Markets coin charts offer an optional recorded-trade overlay. The user must manually match a ledger alias to the displayed coin; no ticker match is applied automatically. Markers reset when changing coins. Only saved USD executions within the visible period are shown, at their actual recorded unit price and UTC date. The overlay is disabled on USDT charts, and shows at most the most recent100 visible fills. It does not place or monitor orders, and simulated fixtures are never inserted into production portfolios.

## Data and runtime limits
All feeds use fixed HTTPS provider hosts, existing bounded response sizes and a30-second upstream operation deadline. The server authenticates every research route, applies provider quotas and preserves source timestamps when cached responses are served during an outage. Public validated responses use existing bounded SQLite/PostgreSQL caching; no personal trades or watchlists enter the shared provider cache. Coin/category identities are validated, and previously loaded category metadata may authorize coin details for up to24hours without arbitrary symbol guessing.

The public-data-only version does not implement CoinGlass's proprietary liquidation heatmaps, verified on-chain whale attribution or continuous push/email monitoring. No subscription, exchange trading credential, wallet signing permission or order execution is introduced. Venue access may vary by region or hosting provider; unavailable rows remain explicit instead of being replaced with estimates.

## Primary references
- https://alternative.me/crypto/fear-and-greed-index/
- https://coinmarketcap.com/api/documentation/pro-api-reference/global-metrics
- https://docs.coingecko.com/demo/reference/coins-markets
- https://docs.coingecko.com/demo/reference/coins-id-tickers
- https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/
- https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints
- https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Long-Short-Ratio
- https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price
- https://bybit-exchange.github.io/docs/v5/market/long-short-ratio
- https://bybit-exchange.github.io/docs/v5/market/tickers
- https://www.okx.com/docs-v5/en/
- https://docs.coinglass.com/reference/authentication

## Validation
Backend tests cover provider schemas, source identity, negative/zero funding, ratio units, malformed timestamps, data gaps, stale cache behavior, narrative identity fallback, watchlist limits/account isolation and authenticated routes. PostgreSQL integration tests exercise the new watchlist table and research routes. Node tests cover race protection, safe links/escaping, source-aware quote units, narrative search/pagination, watchlist behavior, depth, funding/OI formatting and manual USD trade overlays. Live checks verify the actual public endpoints; they do not guarantee provider uptime.


Hosting: a single Vercel function region (Frankfurt, fra1) is configured. Bybit documents that US-hosted IPs are restricted; the default US region therefore cannot fetch its public market endpoints. This changes the existing function location, adds no proxy or API credentials, and retains normal provider restrictions and HTTPS database access. Public feed availability is still validated per venue.

## Account and chart workspace upgrade (October 2026)

Connections supports a dedicated Binance HMAC read-only Spot account. Credentials use AES-256-GCM with a fresh nonce and account/connection identity as authenticated data. Configure `ORBIT_EXCHANGE_KEY` as a URL-safe base64 encoding of 32 random bytes in the server environment; keep it stable and backed up securely. Changing or losing this key requires reconnecting accounts. Never commit it. The app refuses to save credentials until encryption is configured, and rejects keys with unverifiable or enabled mutation permissions. No trading, withdrawal or transfer endpoints are implemented. Live credentials were not available for end-to-end exchange testing; provider behavior and account isolation are covered with fixtures.

Spot free/locked balances are snapshots, not a purchase ledger. Curated Binance asset mappings receive indicative CoinGecko values where available; unknown assets stay unpriced. Wallet, exchange and recorded-trade holdings remain separate on coin pages to avoid double counting. Price changes applied to current quantities are estimates of price movement, not historical investment returns. Insights checkpoints preserve observed portfolio values; acquisition history still requires verified trades/imports.

Public addresses can be saved across selected compatible EVM networks, including Select all EVM. A Bitcoin/Solana/etc. address must use its own network family; selecting every unrelated chain would produce invalid address interpretations. Batch validation is atomic and duplicate registrations are skipped. The account limit is 50 connected network/address pairs.

Chart Studio expands loaded provider history and supports SMA/EMA, Wilder RSI, MACD, crosshair inspection, trend/horizontal lines, Fibonacci retracements, zoom/pan, and account-saved drawings/indicator setups. Indicator periods count provider observations, not necessarily daily candles. The safe declaration editor accepts EMA(n), SMA(n), RSI(n), and MACD(fast,slow,signal); it does not execute arbitrary code and is not a Pine Script runtime. Chart drawings are annotations, not exchange orders. Coin alerts are checked manually against a fresh USD CoinGecko observation, with account-saved thresholds and event history; no background/push/email service is claimed.

Market detail pages provide account watchlist stars, matching known holdings and USD alert controls. Learning includes concise sourced guides and private plain-text notes. Profile allows a display name and current-password-verified password changes; changing the password revokes all sessions. Theme choice is stored in browser preferences; API credentials are never stored there.

Research latency: unrelated market operations no longer share a network-duration cache lock or browser queue. Identical keys still coalesce; market reads allow four concurrent actions per account with the existing shared quota. Wallet/exchange provider mutations retain their single-operation limit. RSI checks eight assets using four workers, propagating the request deadline and public cache callbacks. A measured live cold run produced eight valid readings in about 9 seconds; cached reads were effectively instant. Research views additionally reuse results for 60 seconds, with an explicit refresh action.

News defaults to GDELT public index headline metadata and external publisher links, with a visible search fallback on rate limits/outages. No article bodies or images are copied. Local live GDELT checks returned rate limits; availability depends on the public service. A production-licensed NewsAPI configuration remains optional.

Methodology: Binance API restrictions https://developers.binance.com/en/docs/catalog/core-trading-wallet/api/rest-api/account ; TradingView EMA https://www.tradingview.com/support/solutions/43000592270-exponential-moving-average/ ; MACD https://www.tradingview.com/support/solutions/43000502344-moving-average-convergence-divergence-macd-indicator/ ; GDELT https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/ .

## Recheck: reliability and data freshness

A second review fixed alert form replacement during unrelated chart refreshes, delayed watchlist-state races, unfinished indicator drafts disappearing on chart actions, and overlapping setup save/load operations. Watchlist actions now wait for confirmed account state and offer a retry on failure. Tiny coin holdings retain significant digits instead of being displayed as zero. Exchange parsing preserves complete supported decimal precision and rejects malformed permission/account objects and unexpected nonboolean permission flags.

Independent sentiment feeds now run concurrently with the same request deadline and persistent-cache context. A live cold check returned all three feeds in 1.06 seconds. Outdated daily sentiment/index observations and missing latest completed UTC RSI candles are rejected. News for validated category coins survives a rankings-provider outage. Legacy trade mutations now recheck the session after acquiring the account write lock, preventing an in-flight request from committing after session revocation; this scenario is tested on SQLite and PostgreSQL.

## Explicit intervals, drawing studio and Pine indicators

Exchange charts accept 15m, 1h, 4h, 1d and 1w independently of history range. Binance supplies native buckets. Coinbase 4h/weekly candles aggregate consecutive hourly/daily buckets aligned to UTC; incomplete and still-forming aggregate buckets are omitted and counted in coverage. Excessive page/candle requests fail with an actionable range/interval message. Real reported exchange volumes are retained and summed for complete aggregate buckets. CoinGecko remains provider-sampled. A verified supported coin can switch directly from a CoinGecko view to Binance 4H/1D/1W candles; the quote changes from USD to USDT and is labeled explicitly.

Chart Studio occupies the viewport and includes Focus Chart mode. SVG pointer positions use the screen transformation matrix, fixing misplaced anchors when the viewBox is letterboxed. Candle snapping, anchor previews, exact UTC time/price inputs, Fibonacci extensions/reversal, drawing removal, indicator toggles and interval changes are supported. Drawings retain real time/price coordinates on same-quote interval changes. A quote change clears annotations with an explanation rather than treating USD and USDT as converted prices. Old default chart setups remain loadable.

The Pine indicator editor accepts a bounded subset: indicator declarations, input defaults, typed variables, arithmetic and history, EMA/SMA/RMA/RSI/MACD, BB/stdev, ATR, highest/lowest, math operations, plot and hline. It uses a whitelist parser with no eval, limits source/rows/plots/calculation budget, reports unsupported lines, and never applies partial failed output. Custom oscillator plots share a common pane and scale. Applied source can be retained in account chart setups. User input() defaults are edited in source; unsupported style options are rejected. Genuine high/low/open and volume require a provider that supplies those candle fields.

The supplied Crypto Strategy Lab example is a strategy with broker/order simulation and request.security, and the attachment stops midway through its Pullback logic. It is rejected at strategy() rather than presented as a working simulation. A clearly labeled MPL-attributed visual companion plots its EMA50/200, Bollinger and prior Donchian channels; it does not simulate trades or returns. Full Pine strategies need a separately validated runtime and emulator. PineTS was researched but not added blindly: its current package carries AGPL licensing and runtime code compilation; broader integration requires separate review.

Primary references: Binance public market-data endpoints https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints ; Coinbase candles https://docs.cdp.coinbase.com/exchange/reference/exchangerestapi_getproductcandles ; SVG geometry https://developer.mozilla.org/en-US/docs/Web/API/SVGGraphicsElement/getScreenCTM ; strategy execution https://www.tradingview.com/pine-script-docs/concepts/strategies/ ; PineTS https://github.com/LuxAlgo/PineTS .
