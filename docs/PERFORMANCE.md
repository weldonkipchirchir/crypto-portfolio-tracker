# Local burst performance baseline

Recorded: 2026-10-26T20:24:40Z

## Result

This single local run did **not** handle a 1,000-request burst without errors. It does not measure production Vercel/Neon capacity.

| Endpoint | Concurrent attempts | HTTP 200 | HTTP 503 | Connection errors | Success p95 | Successful req/s during burst |
|---|---:|---:|---:|---:|---:|---:|
| `/app.html` | 20 | 20 | 0 | 0 | 13.7 ms | 1119.88 |
| `/api/state` | 20 | 20 | 0 | 0 | 67.6 ms | 279.09 |
| `/app.html` | 100 | 78 | 0 | 22 | 42.1 ms | 1397.54 |
| `/api/state` | 100 | 29 | 3 | 68 | 123.4 ms | 223.42 |
| `/app.html` | 1000 | 226 | 0 | 774 | 657.8 ms | 269.87 |
| `/api/state` | 1000 | 150 | 74 | 776 | 707.3 ms | 112.19 |

p95 describes successful requests only; failed requests must not be excluded when assessing whether a burst passed. Throughput above is measured over one short burst, not sustainable requests per second.

All five sequential post-burst portfolio checks returned HTTP 200. Successful state responses were validated against the expected account identity and 20 fixture trades. No cross-account response was observed among successful responses.

## Scope and method

Async clients released together; arrival scheduling is OS-dependent. Separate server process, same machine. One request per client, no retries. Latency includes connect, queue and complete response. HTTP 200 state responses checked for account identity and 20 trades. Static assets use local HTTP server, not production CDN.

- 100 disposable accounts, 20 trades each, no wallets. 1,000 requests reuse those 100 identities; this is not 1,000 simulated browsing users.
- No production traffic, production credentials, existing portfolio database or provider API calls.
- Separate local server process; generator and server share this Windows machine. Windows TCP scheduling and connection reset behavior affect the result.
- Production serves public assets from Vercel infrastructure, so local HTML results are not a CDN benchmark.
- Local server uses the existing bounded defaults: 24 workers and backlog 32. It deliberately sheds overload with 503; some attempts fail at the TCP layer. This test does not isolate each failure to one bottleneck.
- No retries, no warmed sustained-load phase and no repeated statistical trials. Bursts are 20, 100 and 1,000 requests per endpoint, with a 10-second request deadline.
- No chart cache misses, login hashing, wallet synchronization, external exchange latency, multi-region traffic or PostgreSQL load is covered.

## Re-run

```powershell
python load_test.py --output performance-local.json
```

The tool binds only to loopback and uses a temporary SQLite fixture. It offers no remote target option. The fixture is removed on normal completion. Tokens are never written to the report.

## Production validation still needed

1. Use a staging Vercel deployment connected to a disposable Neon branch and representative fixture portfolios.
2. Ramp sustained traffic through 10, 50, 100, 250, 500 and 1,000 concurrent clients; record arrival rate and completed requests per second separately.
3. Test static assets, authenticated state, cached markets and controlled provider stubs separately. Then measure provider-limited routes within their quotas.
4. Record p50/p95/p99, failures, Vercel throttles, cold starts, database pool wait time and active connections. Stop on sustained overload or an agreed cost ceiling.
5. Check a target such as <1% unexpected errors and p95 <2 seconds for cached authenticated reads before claiming readiness. These are proposed acceptance criteria, not measured results.

## Architecture findings

- Current cloud pool allows 12 database connections per worker with 16 queued waiters. Scale-out multiplies pools; a platform concurrency ceiling is not a guarantee of database capacity.
- Confirm the production DATABASE_URL uses Neon’s pooled hostname without exposing the credential; tune per-worker pool size against observed database limits. Do not simply increase connection counts.
- Market routes enforce per-account budgets (60 actions/minute and four active actions). Polling limits, request coalescing and shared caches matter as active users grow.
- Wallet provider operations have a separate 12 actions/minute budget and one active action per account. Rejected quota requests should be reported separately from unexpected infrastructure errors.
- Keep the local resource limits. Raising them based only on this loopback run would hide overload without proving production scalability.

Official references: [Vercel concurrency scaling](https://vercel.com/docs/functions/concurrency-scaling), [Vercel function limits](https://vercel.com/docs/functions/limitations), [Neon serverless connection pooling](https://neon.com/docs/guides/serverless-connection-pooling).
