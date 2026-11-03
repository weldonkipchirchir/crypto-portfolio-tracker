# Market explorer

Overview bubbles default to the top 250 provider-ranked coins. Coverage can be 20, 50, 100, 150 or 250. Search and gainers/losers filters operate inside that ranked coverage; unavailable return observations are excluded, so the visible count may be lower. 24h, 7d and 30d returns come from the existing cached CoinGecko markets feed. No additional per-coin request is made for filtering, motion or sizing.

Bubble radius uses a bounded square-root scale of absolute return, market capitalization, or reported 24h volume. Floating paths are independently randomized and bounded inside a 900 by at-most-650 SVG canvas, allowing overlap. Paused freezes animation; Readable grid restores a static, scrollable, separated layout. Reduced-motion preferences disable animation. Keyboard focus and hover pause an individual bubble. A selected coin opens the existing returns calculator.

Data > Market movers supports top 50/100/250 coverage, coin search and 24h/7d/30d returns. The distribution bins are disjoint: below -10; [-10,-5); [-5,0); exactly zero; (0,5); [5,10]; above 10 percent. Median weights each coin equally. Advancing share divides positive observations by all available returns in the filtered sample, including unchanged coins. These are snapshot statistics; stablecoins and wrapped assets are retained. They do not measure portfolio P&L, unique capital flows, historical constituents or a broad market index. Volume always uses the reported 24h window.

The UI preserves provider retrieval time and stale status. Browser QA uses an explicitly labeled captured public-feed snapshot, rather than private portfolio data.

## Data desk navigation and momentum
Data views are grouped as Market overview, Technicals, Order flow, Derivatives and Research tools. The last subview in a category is retained while the Data workspace is mounted. The shared status rail reports loading, partial coverage and retained cached observations. Its timestamp is the oldest reported retrieval among the inspected top-level and known child feeds; missing timestamps remain explicitly unreported. It is not a streaming guarantee.

RSI starts with eight curated major coins and offers 20. The momentum distribution and comparison chart use only available, nonstale finite RSI values in the 0–100 range. Inclusive thresholds are <=30 oversold and >=70 overbought; neutral lies strictly between them. Invalid/stale observations remain unavailable. Band buttons filter the cards locally without requesting new candles; chart coverage continues to describe the whole selected asset sample.

Exchange listing summaries count returned eligible rows and distinct exchange names. The optional volume donut aggregates positive reported listing volumes by exchange, showing the top five and remaining exchanges. Overlapping pairs may be counted; the result describes the returned sample, not global exchange dominance or unique capital. Missing/nonpositive volumes and stale rows do not contribute. Missing spreads stay unavailable.

## Market screener and Bitcoin comparison
Market movers supports direction filters, rank/return/24h-volume sorting, and tile or compact table layouts. Filters, sorting, layout and reset run locally on the loaded provider sample. Coverage is selected before direction/search filtering. Reset restores 24h, top 250, all coins, rank order and tile layout.

The Bitcoin benchmark is matched by CoinGecko ID `bitcoin` from the loaded sample, independently of search and direction filters. Gaps are coin percentage return minus Bitcoin percentage return over the same selected period, expressed in percentage points. This differs from the return of a BTC-denominated trading pair. Up to five largest positive and five largest negative gaps appear. Equal peers contribute to counts but need no directional bar. If the benchmark is missing, the UI reports unavailable rather than assuming zero.

Market coverage supports up to 500 provider-ranked coins across two bounded pages. Data and bubbles offer a Top 500 selector; default remains 250. Page-two failures retain the validated first page with explicit partial coverage. Listings share the existing five-minute cache.
