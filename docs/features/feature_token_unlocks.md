# Token unlock calendar

Private account-saved events, requiring an exact lowercase coin ID (self asserted, not catalog validated), UTC calendar date, positive token amount, recipient category, and a public HTTPS source link. Orbit does not fetch source links or independently verify entries. No paid subscription or provider is connected. Provider status is explicitly unconfigured; there is no speculative provider API integration.

Optional circulating supply must include its UTC as-of date. Percentage is event amount divided by that entered snapshot, rounded to six decimal places. Neither maximum nor circulating supply creates events or predicts a schedule. Saved events can include historical dates; upcoming means today or later in UTC, with no intraday time. The upcoming calendar groups saved events by date; the table retains past events and provenance. Missing events are not evidence of no unlocks.

Limits: 500 events per account; coin ID 100 characters; recipient 100; source URL 2,000; positive amounts up to 1e30 and at most 18 decimal places. No price valuation, recurring events, edit operation, automatic import, or verification. Delete and re-enter to correct an event. Mutations and reads use database only; all event queries are owner scoped. Source links are not fetched, avoiding server-side request forgery. Deletion requires explicit confirmation.

Integration: call `feature_token_unlocks.init(connection)` at database initialization, dispatch feature `token_unlocks` to `read(connection,user_id,payload)` / `action(connection,user_id,payload)`, and load `feature_token_unlocks.js` through the feature workspace. Transaction/commit handling belongs to the existing dispatcher.

Checks: `python -m unittest feature_token_unlocks_test` and `node feature_token_unlocks.test.cjs`.
