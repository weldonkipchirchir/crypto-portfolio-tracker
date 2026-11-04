# Order-book history heatmap

Private account-scoped archive of explicitly requested, server-verified spot depth samples. Default Coinbase BTC-USD; verified asset selector and Binance USDT pairs supported through the existing microstructure provider. This is sampled quoted liquidity, not liquidation history or executed trades.

`init(c)` creates the archive. `read(c, uid, raw)` accepts `coin_id`, `venue` (`coinbase` / `binance`), and `operation` (`history` default / `capture`). Route through authenticated feature-read. Capture fetches the verified server feed, validates identity, freshness and non-crossed positive levels, recomputes price × base quantity, stores and commits. Client snapshot payloads are ignored. No feature action or scheduler is needed.

Up to 120 samples per account + asset + venue. Minimum spacing 60 seconds matches the current verified feed's 60-second cache. Throttled and history reads make no provider requests. Failed capture does not insert a placeholder. Existing feed fetches trades as well as depth, so uses the existing provider request budget. No new upstream endpoints.

Heatmap uses 24 common absolute-price buckets across returned samples; values sum price × base quantity for each actual returned side/price level. Coinbase notional is USD; Binance is USDT and never relabeled USD. Column x positions use actual receipt timestamps and fixed narrow widths: gaps stay blank, never interpolated. The table reports exact sample timestamps, elapsed gaps and side totals. No background recording; no coverage before the first capture; oldest samples removed at the cap.

Validation: `python -m unittest test_feature_orderbook_history` and `node --test feature_orderbook_history.test.cjs` cover tenant/instrument isolation, retention, freshness/identity/depth rejection, ignored client payloads, minimum spacing, actual cell notional, empty states and time gaps.
