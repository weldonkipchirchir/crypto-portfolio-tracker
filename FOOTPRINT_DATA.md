# Footprint data and top-trader definitions

The Data workspace contains Footprint and Top traders views. Both use read-only public Binance market data and verified product identities. They do not place orders or use saved personal exchange credentials.

## Footprint
The footprint uses up to six pages / 6,000 recent aggregate trade records. Backward pagination is bounded; it is not a full historical archive. Counts refer to aggregate prints, not individual fills or traders. Taker sells populate the bid column; taker buys populate the ask column. Trade quantity is summed at real observed price buckets and UTC time intervals; candle volume is never allocated to invented cells.

Available intervals are 1m, 5m, 15m and 1h. Price-row sizes are automatic or explicitly chosen. The outer boundary bars and forming bars are marked partial. A closed bar is considered covered only when the sample spans both boundaries and the aggregate-ID range is contiguous. Missing intervals remain absent. A 15-minute interval may contain only a few bars in a recent bounded sample.

Bar details contain sample OHLC, taker volumes, delta, minimum/maximum running delta, aggregate-print count/average size, sample VWAP and POC. POC is the base-volume row with greatest observed volume. Diagonal imbalance compares buys with sells one row below, or sells with buys one row above, using a nonzero denominator. The default threshold is 300%.

Optional layers show a displayed-sample volume profile, cumulative sample VWAP, POC outlines, diagonal imbalances, base-volume pane and sample CVD (starting at zero at the first displayed bar). The unit selector changes cells/profile to USDT notional; USDT is not USD. The price-chart link opens the existing technical chart tools for RSI, MACD and other indicators.

Raw prints are cached only in worker memory; the smaller aggregate view can use the shared market cache. Refresh is manual by default. Optional 30-second polling pauses when the view/page is hidden and is cleaned up when the component is destroyed. Stale/provider failures are labeled; spot and perpetual data are never silently substituted for each other.

## Top traders
The account and position endpoints are separate. Binance's cohort is the top 20% of users by margin balance. Account ratios count each net-long/net-short account once. Position ratios report proportions of the cohort's net-long/net-short positions. Neither endpoint identifies named traders or their wallets.

Up to 30 provider observations are displayed for 5m, 15m, 1h, 4h or 1d periods. Fractions, declared ratios, pair identity, observation dates and latest freshness are validated. Failed feeds remain independently unavailable; they are not estimated. Regional restrictions, rate limits or future authentication requirements may apply. If needed, a dedicated server-only `BINANCE_MARKET_DATA_API_KEY` can be configured. This integration never reuses personal account connection keys.

No absorption/divergence trading signal, liquidation map, open-interest change or whole-market CVD is inferred from this bounded footprint sample.

## Candle history and zoom
The footprint terminal also loads same-venue Binance OHLC candles for one day, seven days, 30 days, one year, or all available exchange-pair history. Resolution is respectively 1m, 15m, 1h, 1d, or 1w. All available uses weekly candles from the earliest returned listing history, not the coin's lifetime before listing. Requests are capped at six pages of 1,000 candles; invalid or incomplete responses fail explicitly. Zoom and older/newer navigation use the loaded candles without extra requests. Ctrl-wheel zoom is available on the chart. At 12 or fewer visible candles, matching-interval recent bars reveal executed footprint rows only if every visible candle is present in the same-venue trade sample. Other historical bars show OHLC and an explicit unavailable-footprint notice. No bid/ask rows are reconstructed from OHLC.
