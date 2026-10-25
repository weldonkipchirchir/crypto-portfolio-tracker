# Deploy Orbit to Vercel

## Storage and privacy
Local runs keep using portfolio.sqlite3. When DATABASE_URL is configured, the app uses PostgreSQL. Hosted mode refuses to use temporary SQLite storage. Local accounts, sessions, wallets and trades are excluded from Git and deployment; the hosted app starts with a fresh database. No automatic upload of local financial records occurs.

## Required Vercel setup
1. Import weldonkipchirchir/crypto-portfolio-tracker. Framework: Other. Root: repository root. Use the included vercel.json and Python 3.12 runtime. The public output directory is deliberately empty: the Python handler serves only explicit frontend routes and authenticated API endpoints.
2. Connect a Neon PostgreSQL database through Vercel Marketplace, or configure an existing PostgreSQL DATABASE_URL. Use the provider's pooled connection URL and separate databases/branches for Preview and Production. Store credentials only in Vercel environment settings, never Git or chat.
3. Set ORBIT_SECURE_COOKIE=1 and ORBIT_REGISTRATION_EMAIL=weldonkipchirchir23@gmail.com. Registration is restricted to that email. The hosted entry point fails closed if these or DATABASE_URL are missing.
4. Automatic Vercel deployment and production domains are accepted from trusted runtime environment variables. For a custom domain add ORBIT_ALLOWED_HOSTS as exact comma-separated hostnames (no scheme/path/wildcard).
5. Optional provider keys (ETHERSCAN_API_KEY, COINGECKO_DEMO_API_KEY and RPC URLs) belong in environment settings. Supported balance/history coverage remains provider-dependent.
6. Deploy to a protected Preview first. Register the owner, verify that login and wallet/trade records survive another deployment, and check provider errors. Then promote to Production.

## Runtime behavior
The Python entry point is api/index.py. Schema creation is idempotent and coordinated by a PostgreSQL transaction advisory lock. Writes use transactions; trade modifications additionally acquire a per-account transaction lock to prevent concurrent overselling. Passwords and session handling retain existing protections. Sign-in quotas, provider quotas and per-account provider leases use PostgreSQL so instances share them. Provider action deadlines remain 30 seconds and the function limit is 60 seconds. Hosted database transport requires TLS.

The hosted owner restriction is for a personal deployment. Password recovery, MFA, operational monitoring, managed database backup/restore drills and a public multi-user launch review remain future work. Dashboard privacy is display-only, not access control.

## Checks
- `python -m unittest discover -q` runs local regression tests with disposable SQLite databases.
- `node test_ui.cjs` verifies dashboard allocation and filters.
- Set ORBIT_TEST_DATABASE_URL to a disposable PostgreSQL test database and run `python -m unittest test_cloud_storage -q`. Tests create unique schemas and remove those schemas afterward. Never use a real portfolio database for tests.

## Publishing
Authenticate Git with the intended GitHub account and run `git push -u origin codex/vercel-deployment`. Vercel CLI authentication uses `npx vercel login`; connect the repository from Vercel to enable deployment on pushes. Repository visibility is managed on GitHub; this workflow does not change it.
