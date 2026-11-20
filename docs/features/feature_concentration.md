# Portfolio concentration

Roadmap feature 13 is a local snapshot analysis module registered as `concentration`. It consumes `OrbitPerformance.positions(state)` so connected exchange deduplication follows the existing position pipeline. Connected holdings and recorded trades are selected separately; no ledger/connected combined denominator exists.

Shares use finite nonnegative saved USD values. Missing values are counted and excluded; stale/incomplete positions remain included with visible counts. Largest-group share, top-five share and HHI (sum of squared shares on 0–1 scale) describe the selected grouping, not predicted risk. Zero or invalid total has unavailable metrics.

Exact wallet asset IDs, exchange asset IDs and exact ledger symbols have separate identity namespaces. Network applies to wallet positions; unavailable network/account metadata stays explicit. Exchange account keys come from existing connection snapshots. Wallet positions do not expose per-account splits, so account grouping explicitly labels that limitation.

Classification is opt-in from a position's `provider_metadata` object with `verified: true` and a nonempty `provider`. `is_stablecoin` must be boolean; `categories` must contain nonempty strings. Existing positions without this verified metadata can also match exact IDs in the selected provider sample, described below. Symbols, aliases and prices do not establish classifications. No per-asset requests are made; classification modes may load one bounded category sample as described below. Narratives group each exact sorted tag set once, avoiding overlapping-category double counting.

The accessible bar figure is accompanied by the full breakdown table. Source/group controls reload through the module host and detach listeners on cleanup.

Validation: `node --test feature_concentration.test.cjs`.

## Selected provider taxonomy samples

Stablecoin and narrative modes now make one `feature-read` request with `feature: concentration` and a fixed category allowlist. Asset/network/account modes do not request taxonomy. Stablecoins use CoinGecko's official `stablecoins` category ([official taxonomy](https://www.coingecko.com/en/categories/stablecoins), verified November 4, 2026). Narratives offer the existing RWA, AI, DeFi, gaming, meme, Layer 1 and Layer 2 taxonomy through `market_intelligence.narratives`.

The read-only backend uses an eight-second provider deadline, a private 15-minute sample cache, and a one-minute failure cache; the stablecoin request takes only page one with `per_page=250`. Narrative loading reuses the existing bounded provider loader. Neither path paginates or requests individual assets, and no action operation is exposed.

Only positive exact CoinGecko ID membership is applied. Missing IDs, missing identities and failures remain unclassified; absence from a ranked category sample cannot establish non-stablecoin or other-sector status. The display shows selected category, sample size, timestamp, stale status and incomplete coverage. Explicit provider-verified metadata on an exact position remains accepted; negative stablecoin metadata is not used to imply a complete complement.

Additional validation: `python -m unittest feature_concentration_test`.
