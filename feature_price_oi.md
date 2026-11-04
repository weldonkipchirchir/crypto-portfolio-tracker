Price and open interest (roadmap 20)

Read-only Binance USDⓈ-M BTCUSDT, ETHUSDT and SOLUSDT perpetual history. Coin IDs reuse exchange_charts.ASSETS and market_microstructure.identity. Three public requests maximum per cache miss; providers.request_json uses the shared 15-second deadline; cache TTL five minutes, at most twelve asset/period entries. No credentials, actions or database writes.

Periods 5m, 1h, 4h and 1d are valid for both klines and openInterestHist. Window is min(288 intervals,29 days); no pagination or promise of full lifetime coverage. Binance exposes only the latest month of OI statistics. API failures retain other observations and show errors.

Price is kline field 1 (open), timestamp field 0. Volume field 5 is the subsequent candle base-coin total and is omitted until field 6 close time has passed. OI uses original timestamp, sumOpenInterest as base coin and sumOpenInterestValue as USDT quote value, never USD or contract count. Funding uses fundingTime/fundingRate for the same symbol. All series are outer-joined at exact original timestamps, without rounding, nearest-neighbor matching or filling; charts show separate samples. OI period-end versus price candle-start semantics are explicitly disclosed.

Official source: https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data (Kline/Candlestick Data, Open Interest Statistics, Get Funding Rate History). Read 2026-11-04. No inferred market-direction signals.

Integration: feature_price_oi.read(c,uid,raw); browser window.OrbitFeatureModules.price_oi. No shared integration files owned by this module.

Checks: python -m unittest feature_price_oi_test; node feature_price_oi.test.cjs.
