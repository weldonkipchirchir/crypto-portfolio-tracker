# Market explorer

Overview bubbles default to the top 250 provider-ranked coins. Coverage can be 20, 50, 100, 150 or 250. Search and gainers/losers filters operate inside that ranked coverage; unavailable return observations are excluded, so the visible count may be lower. 24h, 7d and 30d returns come from the existing cached CoinGecko markets feed. No additional per-coin request is made for filtering, motion or sizing.

Bubble radius uses a bounded square-root scale of absolute return, market capitalization, or reported 24h volume. Floating paths are independently randomized and bounded inside a 900 by at-most-650 SVG canvas, allowing overlap. Paused freezes animation; Readable grid restores a static, scrollable, separated layout. Reduced-motion preferences disable animation. Keyboard focus and hover pause an individual bubble. A selected coin opens the existing returns calculator.

Data > Market movers supports top 50/100/250 coverage, coin search and 24h/7d/30d returns. The distribution bins are disjoint: below -10; [-10,-5); [-5,0); exactly zero; (0,5); [5,10]; above 10 percent. Median weights each coin equally. Advancing share divides positive observations by all available returns in the filtered sample, including unchanged coins. These are snapshot statistics; stablecoins and wrapped assets are retained. They do not measure portfolio P&L, unique capital flows, historical constituents or a broad market index. Volume always uses the reported 24h window.

The UI preserves provider retrieval time and stale status. Browser QA uses an explicitly labeled captured public-feed snapshot, rather than private portfolio data.

## Data desk navigation and momentum
Data views are grouped as Market overview, Technicals, Order flow, Derivatives and Research tools. The last subview in a category is retained while the Data workspace is mounted. The shared status rail reports loading, partial coverage and retained cached observations. Its timestamp is the oldest reported retrieval among the inspected top-level and known child feeds; missing timestamps remain explicitly unreported. It is not a streaming guarantee.

RSI starts with eight curated major coins and offers 20. The momentum distribution and comparison chart use only available, nonstale finite RSI values in the 0–100 range. Inclusive thresholds are <=30 oversold and >=70 overbought; neutral lies strictly between them. Invalid/stale observations remain unavailable. Band buttons filter the cards locally without requesting new candles; chart coverage continues to describe the whole selected asset sample.

Exchange listing summaries count returned eligible rows and distinct exchange names. The optional volume donut aggregates positive reported listing volumes by exchange, showing the top five and remaining exchanges. Overlapping pairs may be counted; the result describes the returned sample, not global exchange dominance or unique capital. Missing/nonpositive volumes and stale rows do not contribute. Missing spreads stay unavailable.
