# Markets: ranking, research and implementation

## Shipped behavior
- Up to 250 provider-ranked coins, ordered by market-cap rank, with search, rank/name/24h-volume/24h-change sorts and 25/50/100-row pagination. A live check returned 249 valid ranked records; invalid or unranked rows are excluded.
- Click a coin to open a research page with actual historical USD prices for 1, 7, 30 and 90 days. The SVG chart has an accessible description and a recent-observations table. Changing coins/ranges uses request sequence checks so late responses cannot overwrite a newer choice.
- Current price, market cap, FDV, 24h volume, ATH/ATL and circulating/total/maximum supply are provider snapshots. Unknown maximum supply is not zero or an unlimited-supply claim. Current supply is not an unlock schedule.
- Plain provider descriptions, categories and safe HTTPS project/source links. Market records use CoinGecko IDs; they do not automatically bind a same-ticker wallet token or establish personal cost/P&L.
- Protocol revenue from DefiLlama is displayed only when the summary confirms the exact CoinGecko ID. DailyRevenue represents fees retained by the protocol, not company profit, fees paid by all users or token-holder income. Unsupported or mismatched projects are unavailable, not estimated. The initial slug candidate is the coin ID; no ticker guessing is used.

## Providers and configuration
CoinGecko public API works without a key subject to provider/IP limits. An existing COINGECKO_DEMO_API_KEY can be stored in server/Vercel environment variables; requests send the documented x-cg-demo-api-key header. Rankings may differ from CoinMarketCap because the source is CoinGecko. Attribution is shown in the UI.

DefiLlama revenue uses the public `/summary/fees/{slug}?dataType=dailyRevenue` endpoint. Unlock data is a separate paid API category. An existing DEFILLAMA_API_KEY enables the documented keyed `/api/emissions` API. The app never subscribes or purchases access. It matches gecko_id exactly and exposes only validated summary metrics and dated event objects with verified timestamps; an unsupported event shape is not guessed. API keys never reach the browser or stored public cache. Without a configured API key, the unlock panel clearly states the requirement and links to provider coverage. Full dated schedules cannot be verified live without licensed access.

## Security, caching and data integrity
Authenticated JSON API routes enforce existing host/origin controls. Markets has a separate shared 60-actions/minute account budget and per-account lease. Provider requests retain bounded body sizes and deadlines. Listings are cached five minutes, details ten minutes, charts five minutes and fundamentals thirty minutes. Public validated responses are shared in SQLite/PostgreSQL across serverless instances, with a 400-record cap; process caches are also bounded. Cached data is explicitly stale during provider failure. No portfolio records or secrets are cached with market responses.

Strict coin-ID whitelist validation limits detail/chart calls to the ranked directory. Finite bounded numbers, timestamp/range checks and exact provider identity prevent malformed data from becoming fake points or records. Descriptions are stripped to plain text and shortened, metadata is escaped, links require HTTPS, and no third-party logos/scripts are fetched by the browser.

## Primary research
- CoinGecko markets: https://docs.coingecko.com/demo/reference/coins-markets
- CoinGecko historical chart: https://docs.coingecko.com/demo/reference/coins-id-market-chart
- CoinGecko rate limits: https://docs.coingecko.com/docs/errors-and-rate-limits
- DefiLlama free API: https://api-docs.defillama.com/llms-free.txt
- DefiLlama fee/revenue definitions: https://docs.llama.fi/analysts/data-definitions
- DefiLlama paid unlock endpoints: https://api-docs.defillama.com/llms-pro.txt

## Tests
`python -m unittest discover -q`, with ORBIT_TEST_DATABASE_URL for disposable real PostgreSQL checks. Existing UI checks plus `node market_dashboard.test.cjs` cover actual charts, unknown supply, safe links, escaping, pagination and late-response races. Browser tests cover Bitcoin/Aave details, ranked listings, search, range switches, supply and exact-ID-matched revenue. Provider availability and paid unlock access remain external dependencies.


## Chart and news upgrade
Charts now offer 1D, 7D, 30D, 90D, 1Y and ALL, with line/candlestick views. ALL means all currently accessible provider history, limited to the past 365 days on CoinGecko Demo; it does not promise history since launch. OHLC comes directly from `/coins/{id}/ohlc`, not line-point aggregation. Candle close timestamps and provider auto intervals (30 minutes for 1D, four hours for 7/30D, four days for 90D/1Y/ALL) are disclosed. The observed start/end, retrieved time, stale warnings and recent OHLC table remain visible. Invalid OHLC ordering, future/nonfinite values and duplicate timestamps are filtered. Line/type/range/coin async responses cannot overwrite a newer selection.

Coin news loads only on request. Without configured licensed access, the panel offers an external Google News web search by coin name and cryptocurrency context; no Google RSS or publisher feed is copied. Optional NEWS_API_KEY enables NewsAPI `/v2/everything` using the server-only X-Api-Key header, English title search with a quoted coin name and crypto context, the past30days and bounded pagination. Vercel additionally requires NEWS_API_PRODUCTION_LICENSED=1. Configure that flag only for an existing plan permitting production use; free Developer keys are restricted to local development and testing. No account or subscription is created by the app. Only sanitized headline, publisher, publication date and HTTPS link are stored (15-minute cache); full article text/images are omitted. Name matches can include namesakes; no contract-level news identity is claimed. Licensed headlines have fixture coverage only until a valid provider key is configured.

Additional official research:
- https://docs.coingecko.com/demo/reference/coins-id-ohlc
- https://newsapi.org/docs/endpoints/everything
- https://newsapi.org/docs/authentication
- https://newsapi.org/pricing

Regression coverage: `python -m unittest test_coin_market test_market_news test_markets_api -q`, `node market_dashboard.test.cjs`; real CoinGecko Bitcoin1D OHLC returned48candles and ALLline returned366dailyobservations during implementation.


## Local chart viewport
Zoom in/out, Reset zoom, Earlier and Later operate on validated loaded observations for both chart styles, without extra provider requests. The chart rescales to the visible rows and shows visible/loaded counts and exact visible period. The minimum viewport is five observations (or the complete dataset if smaller). Coin, range and chart-type changes reset the viewport. This magnifies existing data; it does not create finer-grained candles or extend provider history. Regression checks cover zoom limits, pan bounds, reset and no additional provider calls.

Longer-history alternatives researched: Binance spot `/api/v3/klines` and Coinbase Exchange product candles accept paged historical time ranges. These are individual exchange/pair histories, limited by listing date and data gaps; neither promises lifetime history for all250coins. Binance has per-request/rate limits; Coinbase documents300candles per request and missing intervals without trades. TradingView hosted widgets provide their own data with instrument restrictions; Advanced Charts/Lightweight Charts libraries do not include market data. No additional data vendor is enabled by this viewport update.
- https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints
- https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles
- https://www.tradingview.com/charting-library-docs/latest/connecting_data/datafeed-api/
