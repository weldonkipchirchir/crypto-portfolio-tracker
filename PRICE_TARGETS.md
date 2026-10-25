# Price targets: research, behavior and limits

## Behavior implemented
Targets are account-saved, exact USD unit-price conditions for nonzero assets currently in connected wallets. A token uses chain plus canonical contract/mint identity; native assets use chain:native. Same tickers never combine identities. Comparisons are inclusive: At or above (>=), At or below (<=).

Saving a target checks fresh saved provider quotes immediately. Global price refresh also evaluates saved targets. This is explicit observation-based checking, not background monitoring, trading, email or push. An existing matching quote observed in the last 15 minutes can produce an event as soon as the target is saved. The event records when Orbit checked it and when the quote was observed; it does not claim when the market first crossed.

Rules are recurring. After a matching quote creates an event, a newer valid quote must move outside the condition before a later match can create another event. Repeated or older timestamps do not duplicate events. Stale, unavailable, manual, conflicting same-time or untrusted-source quotes cannot trigger or rearm. Eligible sources are CoinGecko for native assets and DEX Screener for contract-priced tokens. A stale holding balance can still have an eligible fresh market quote; a price target does not verify the balance.

The server calculates conditions using Decimal values. Client-provided quotes, event times, ownership fields and results are ignored. Transactions use the existing account lock on PostgreSQL or immediate write transactions on SQLite. No network request is added by target evaluation.

## Limits
Maximum 30 active rules and 200 recorded events per account. Identical rule duplicates are rejected. The event-cap warning is visible; further matches cannot be recorded after capacity is reached. Existing events are not automatically deleted. Removing a rule preserves recorded events. Archiving/exporting events and a reusable inbox capacity policy are future work.

## Research
- CoinStats configurable custom alerts: https://help.coinstats.app/en/articles/3573865-how-to-set-up-custom-alerts
- CoinMarketCap per-coin notification/inbox settings: https://coinmarketcap.com/settings/notifications/
- DEX Screener latest pool-quote API: https://docs.dexscreener.com/api/reference

Orbit adopts explicit threshold conditions and an in-app history. It does not claim these products' push delivery or continuous monitoring capabilities.

## Verification
Run `python -m unittest discover -q`, with ORBIT_TEST_DATABASE_URL set to a disposable PostgreSQL database for real cloud-adapter tests. Run `node test_ui.cjs`, `node advanced_dashboard.test.cjs`, and `node target_dashboard.test.cjs`. Tests cover initial matches, recurring crossing/rearm, inclusive boundaries, duplicate timestamps, wrong identities, manual/stale/future quotes, conflicting same-time observations, caps, account isolation, refresh integration and safe asynchronous UI behavior.
