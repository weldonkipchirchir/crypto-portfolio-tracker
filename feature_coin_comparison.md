# Coin comparison

Research module `coin_comparison` selects 2–4 exact CoinGecko IDs from the existing cached top-500 market catalog (default Bitcoin and Ethereum). Shows USD price, market cap, FDV, circulating/total/max supply and 24h USD volume. Unknown or negative metrics display Unavailable.

Each comparison makes one market-listings request and at most four existing market-chart requests. Periods are 30, 90 or 365 days; all-time is deliberately absent because CoinGecko Demo history is limited to 365 days. Existing server caches apply. Provider coverage, partial catalog, quote-update timestamps, view retrieval time and individual history failures are visible.

History uses the latest real observation per UTC date, intersects exact common dates across every selected asset and rebases each positive opening price to 100 on the same first common date. Zero bases have no index. Missing dates remain missing, and chart lines break across date gaps. Intraday timestamps can differ and are exposed in the observations table. This is price comparison, not portfolio P&L or investment return.

No new backend, persistent data or provider dependency. Registration uses `OrbitFeatureModules.coin_comparison`; binding returns listener cleanup. Run `node --test feature_coin_comparison.test.cjs`.
