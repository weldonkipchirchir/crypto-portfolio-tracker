# Multi-exchange footprint

The standalone `multi_footprint` registry module compares Binance Spot BTC/ETH/SOL USDT instruments against Coinbase Exchange Spot USD instruments. It makes two independent existing `intelligence-flow` requests and uses only each response's unthresholded, service-normalized `large_trades.sample_trades` (at most 100 records). Existing footprint API supports Binance spot/perpetual only; it cannot supply a genuine second exchange.

Each panel validates base, quote and pair identity, removes duplicate IDs, withholds conflicting IDs, rejects invalid or unknown-side records, and groups real timestamped executions at exact observed prices into selected UTC 1m/5m/15m/1h bars. Buy is normalized taker buy (ask); sell is taker sell (bid). Quote notional is recomputed as price × base quantity. Samples and units are separate; USD/USDT are never summed or converted.

All bars are explicitly partial samples with unverified completeness. Missing intervals remain absent. ID discontinuities, long observed time spacing, dropped records and snapshot freshness are reported independently. Time spacing alone is not proof of missing trades. Each refresh replaces samples; no execution archive, polling, candles, inferred price cells, or all-time execution coverage is supplied. One venue failure preserves the other panel. This is a spot comparison under the requested Derivatives registry category, not a perpetual execution comparison.

Validation: `node --test feature_multi_footprint.test.cjs`.
