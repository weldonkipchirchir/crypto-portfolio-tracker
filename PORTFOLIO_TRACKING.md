# Daily portfolio tracking

The production schedule invokes GET /api/cron/portfolio-daily during the 23:00 UTC hour every day. No user session is required. Vercel must have a server-only CRON_SECRET (32â€“256 URL-safe letters/digits/underscore/hyphen) before deploying this change. Vercel sends it as an Authorization Bearer header. Missing/wrong secrets are rejected before hosted database initialization. Never put this secret in client code or a URL.

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
