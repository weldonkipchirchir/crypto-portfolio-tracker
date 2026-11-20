# Orbit crypto portfolio tracker

Orbit tracks connected wallet and exchange balances, recorded trades and weighted-average profit or loss. Its frontend uses plain JavaScript, HTML and CSS. The Python backend runs locally with SQLite and on Vercel with PostgreSQL.

## Project layout

```text
api/                     Vercel function entry point
backend/
  accounts/              Profiles, authentication helpers and notes
  chains/                Chain adapters and transaction history
  core/                  Paths, CSV safety and request limits
  features/              Independent analytics services and dispatcher
  integrations/          Exchanges, tokens and provider access
  markets/               Prices, charts, news and market research
  notifications/         Email alert delivery
  portfolio/             Accounting, valuation history and reviews
  storage/               PostgreSQL connection and storage layer
  web/                   Explicit public asset allowlist
  server.py              HTTP routes and local server implementation
frontend/
  pages/                 Landing page, workspace and public guides
  scripts/               App, shared, portfolio, markets, charts and features
  styles/                Stylesheets
  assets/                Branding, coin logos and asset metadata
  static/                robots.txt, sitemap and example CSV
scripts/                 Build and test entry points
tests/
  backend/               Python API, accounting and service tests
  frontend/              JavaScript behavior and rendering tests
  fixtures/              Synthetic CSV and Pine fixtures
config/source_paths.json Legacy logical source names to filesystem paths
docs/                    Operations, feature notes and historical reviews
public/                  Generated Vercel output; do not edit
server.py                Stable local launch command
build_static.py          Stable build command
```

## Run locally

Use Python 3.12+ and install the dependencies:

```sh
python -m pip install -r requirements.txt
python server.py
```

Open http://127.0.0.1:8042. Local SQLite data stays at the existing `portfolio.sqlite3` path. Existing environment files, recovery copies, virtual environments and deployment settings have not been moved.

## Verify and build

Node.js 22+ is used in CI; no frontend package installation is required.

```sh
python scripts/test_backend.py
node scripts/test_frontend.cjs
python scripts/build_static.py
```

Backend tests use temporary data, remove hosted credentials from the test process environment and permit loopback networking only. PostgreSQL-specific tests need an explicitly configured disposable loopback `ORBIT_TEST_DATABASE_URL`. These controls are not an OS sandbox.

Public URLs such as `/app.html`, `/app.js` and `/guides/wallet-tracking.html` remain stable. The asset allowlist maps those URLs to frontend source files. The build copies only allowlisted files into `public/`.

## Documentation

- [Development and structure](docs/development.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Security](docs/SECURITY.md)
- [Exchange key protection](docs/EXCHANGE_SECURITY.md)
- [Supported networks](docs/NETWORKS.md)
- [Background portfolio tracking](docs/PORTFOLIO_TRACKING.md)
- [Documentation index](docs/README.md)
- [Previous implementation history](docs/project-history.md)

Accounting uses portfolio-wide weighted-average cost, with purchase fees included. Wallet balances alone do not establish purchase cost. Coverage, stale quotes and unknown values remain explicit; this tracker is not a jurisdiction-specific tax report.
