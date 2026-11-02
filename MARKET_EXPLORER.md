# Market explorer

Overview bubbles default to the top 250 provider-ranked coins. Coverage can be 20, 50, 100, 150 or 250. Search and gainers/losers filters operate inside that ranked coverage; unavailable return observations are excluded, so the visible count may be lower. 24h, 7d and 30d returns come from the existing cached CoinGecko markets feed. No additional per-coin request is made for filtering, motion or sizing.

Bubble radius uses a bounded square-root scale of absolute return, market capitalization, or reported 24h volume. Floating paths are independently randomized and bounded inside a 900 by at-most-650 SVG canvas, allowing overlap. Paused freezes animation; Readable grid restores a static, scrollable, separated layout. Reduced-motion preferences disable animation. Keyboard focus and hover pause an individual bubble. A selected coin opens the existing returns calculator.

Data > Market movers supports top 50/100/250 coverage, coin search and 24h/7d/30d returns. The distribution bins are disjoint: below -10; [-10,-5); [-5,0); exactly zero; (0,5); [5,10]; above 10 percent. Median weights each coin equally. Advancing share divides positive observations by all available returns in the filtered sample, including unchanged coins. These are snapshot statistics; stablecoins and wrapped assets are retained. They do not measure portfolio P&L, unique capital flows, historical constituents or a broad market index. Volume always uses the reported 24h window.

The UI preserves provider retrieval time and stale status. Browser QA uses an explicitly labeled captured public-feed snapshot, rather than private portfolio data.
