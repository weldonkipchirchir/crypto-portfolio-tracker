# Security review

Review date: 2026-10-24. This application remains a local prototype; this review is not a penetration-test certification.

## Threat model

Protect private portfolio records, account passwords, session tokens, and provider API credentials against unauthenticated clients, other signed-in users, malicious websites targeting a localhost service, and malformed input. Public wallet addresses are public on-chain but their association with an account is private. Wallet connection must never request seed phrases, private keys, token approvals, transaction signatures, or withdrawal permissions.

## Implemented safeguards

- Passwords use salted scrypt; unknown-account login computes the same hash operation. Password and email sizes are bounded.
- Session tokens are generated randomly, stored as SHA-256 digests, checked for expiration, and sent with HttpOnly and SameSite=Strict. Expired sessions are pruned at sign-in.
- Every account query and mutation uses account ownership checks. Regression tests exercise cross-account wallet removal and trade isolation.
- Browser requests must use JSON, valid local/configured Host, matching Origin when present, and may not declare cross-site Fetch Metadata. This blocks cross-site form submissions and DNS rebinding against the default local service. Non-browser clients can omit Origin.
- Authentication is limited to 30 attempts per client IP in 15 minutes, with bounded in-memory bookkeeping. Socket reads have a timeout, body size is limited to 1 MB, and extreme numeric exponents/precision and malformed JSON are rejected.
- Ledger mutations acquire an immediate write transaction before reading holdings, preventing concurrent sales from exceeding available quantity.
- Responses include no-store, frame protection, no-referrer, MIME sniffing protection, and a Content Security Policy restricting external resources and outbound connections.

## Before a public launch

- Put a production application server behind HTTPS, with request deadlines and durable distributed rate limits. runtime_security.BoundedHTTPServer supplies a local 24-worker ceiling, a bounded accept queue, socket timeouts, and immediate 503 responses on overload; the stdlib server remains unsuitable as the public production edge. Restarting resets in-memory limits.
- Configure ORBIT_ALLOWED_HOSTS as comma-separated exact hostname values, and ORBIT_SECURE_COOKIE=1 only when served through HTTPS. Do not trust arbitrary forwarded headers. Use an explicit deployment origin behind a vetted proxy.
- Add email verification, secure password reset, user session management, MFA or passkeys, and generic registration responses to reduce account enumeration. The current registration response reveals whether an email exists.
- JavaScript is externalized and script-src is restricted to self; inline event handlers are removed. Style attributes still require unsafe-inline for styles. Maintain DOM escaping and review any future third-party script dependency.
- runtime_security.ProviderBudget supplies same-account non-overlap, 12 operations per minute per user, six globally concurrent operations, and bounded bookkeeping. It is wired around sync, quote refresh, and token/activity inspection before writes. Responses are capped at 4 MiB and requests have deadlines. Balance sync collects provider responses before starting writes. Failed actions count against budgets. Add durable provider quotas, shared limits across instances, and caching for production; process-local limits reset on restart.
- Add encrypted backups and restore tests, database schema migrations, retention and account deletion, privacy policy, and monitored error/audit logs without tokens or sensitive payloads. SQLite data and wallet-to-user associations are currently plaintext at rest.
- Encrypt exchange API credentials with a managed key outside the database, require read-only permissions, and never store withdrawal-enabled keys. No exchange credential storage is implemented yet.
- Commission an independent security assessment and dependency review before accepting public users or handling paid subscriptions.

## Regression tests

Run `python -m unittest discover -q`. Tests use temporary databases and separate local HTTP servers and do not mutate the running portfolio database.
