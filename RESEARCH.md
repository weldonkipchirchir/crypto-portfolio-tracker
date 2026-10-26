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
