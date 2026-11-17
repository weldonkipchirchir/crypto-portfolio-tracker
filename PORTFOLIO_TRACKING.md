# Daily portfolio tracking

The production schedule invokes GET /api/cron/portfolio-daily during the 23:00 UTC hour every day. No user session is required. Vercel must have a server-only CRON_SECRET (32Ã¢â‚¬â€œ256 URL-safe letters/digits/underscore/hyphen) before deploying this change. Vercel sends it as an Authorization Bearer header. Missing/wrong secrets are rejected before hosted database initialization. Never put this secret in client code or a URL.

Each connected account is enabled by default and can pause/resume daily tracking in the Portfolio gain & loss calendar. The UI shows configuration and last successful automatic capture. Local development does not have an automatic scheduler merely because the server is running.

## What is tracked

Automatic capture fetches current supported public prices and applies them to the account's last synchronized wallet/exchange quantities. It does not decrypt exchange keys, place orders, sync balances, or discover newly acquired tokens. Sync balances after external trades, deposits, withdrawals or rewards. Wallet contracts use contract-specific eligible DEX quotes; exchanges use exact saved coin IDs, never a guessed ticker. Unsupported, stale or missing prices remain unpriced. Cached values are not silently carried forward as fresh. The snapshot records the saved-quantity basis and pricing coverage; partial/changed coverage is visible. Calendar changes are not cash-flow-adjusted investment returns. Missing past days are not reconstructed.

Scheduled estimates do not overwrite live wallet/exchange snapshots or ledger prices. Stale workspace reads do not replace a scheduled same-day observation. Explicit user updates can replace that day's final observation, consistent with the existing last-observation-per-UTC-day calendar.

## Operations and limits

A durable per-day lease prevents overlapping jobs. Per-account day markers make retries idempotent; a failed incomplete run can resume without replacing accounts already captured that day. Provider calls occur outside database write transactions. Each capture re-reads owner-scoped saved holdings under a short account lock and writes only that owner's daily record.

The synchronous function has a 45-second work budget (deployment maximum 60 seconds), max 200 accounts per invocation, max 12 unique contract quotes from at most 32 token snapshots, four quote workers and bounded public provider requests. Unavailable contract quotes are marked unpriced. A remaining account backlog or provider failure returns 503 and an aggregate non-secret summary; no balances, wallet addresses, account IDs or keys are returned by the cron endpoint. Monitor invocation failures and pending counts. Vercel does not guarantee retries: large deployments need an external retrying scheduler/queue or a more frequent supported schedule to drain all batches each UTC day. Do not claim every account was captured when a backlog remains.

Vercel Hobby supports daily cron expressions and may trigger anywhere in the configured hour. The scheduler starts only after the secret is configured and a production deployment includes vercel.json's cron entry. Check the project's Cron Jobs page and execution logs after deployment; disabled platform jobs cannot be inferred from source configuration alone. The UI therefore says configured, not guaranteed running.

## Verification

Synthetic temporary-database tests cover two days without sessions, distinct owners, disabled accounts, retries/backlogs, no exchange-key decryption, preserved source balances, fresh-price rejection, stale-read protection, secret authentication and hosted fail-closed initialization. The production job is not considered verified until an authorized invocation completes and the calendar shows its automatic capture.

Verification completed before deployment: 591 Python tests passed (21 optional skips), all 55 JavaScript suites passed, static build and whitespace checks passed. The temporary synthetic UI demonstrated $200 to $220 (+10%) over two daily observations with no sessions during capture, automatic provenance, pause/resume, desktop/390px rendering and no browser errors. No real portfolio was used in that preview.

Production verification: deployment dpl_AC6VRbJ3iJoBWtEep3d61K7vMRgV reached READY and the production alias. A generated CRON_SECRET was added as a Production Secret through stdin; its value was not printed or stored in the repository/local files. The deployed cron endpoint returned 401 without authorization. An authorized request with no user session returned HTTP 200, saved=1, unpriced=0 accounts, pending=false for 2026-11-17. A second request returned already_completed_or_running. This verifies the background handler and idempotence; the first platform-timed invocation will occur in the configured daily hour.


## History workspace and capture resilience
The calendar now includes a saved-value chart with 30-day, 90-day and all-history ranges, a matching CSV export, and explicit breaks across missing dates. It never substitutes zero for missing observations. The chart uses separate mobile geometry for legible labels. CSV names use orbit-value-history; holdings export retains its own name. The tracking card distinguishes setup, paused, waiting, active, overdue and error states, with a next scheduled window rendered in the browser's local timezone. Browser-only save failures remain visible and concurrent preference changes are guarded.

Capture errors are isolated by account. A failed account rolls back its transaction, gets a generic private error/attempt timestamp when storage permits, remains eligible for retry, and does not stop later owners. Saved/unpriced counts increment only after commit. Optional invalid token metadata does not stop the global contract-quote prefetch; an affected owner's invalid saved state is handled as an account error. The cron aggregate includes failed count and returns non-success when any account fails, keeping the daily run resumable.

Validation: 593 Python tests passed (21 optional skips). History/health/export regressions check invalid/future dates, missing values, range selection, disjoint chart paths, neutralized CSV fields, paused/overdue/error copy and escaping. Synthetic browser QA verified CSV content and filename, pause/resume, 390px/desktop layouts and empty browser error logs. Demo charts contain synthetic history, not backfilled user values.
