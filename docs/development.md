# Development and source organization

Start local development with `python server.py`. The root entry point delegates to `backend.server.main`; business modules use explicit `backend.*` package imports. Package `__init__.py` files contain no import side effects.

Frontend files are grouped by responsibility under `frontend/scripts/`. Runtime script URLs remain stable: `backend/web/static_assets.py` uses the source map to translate public URLs to physical files. Do not change public URLs merely to match folders. When adding a source asset, register it explicitly in the allowlist and add its logical source mapping if it does not use a direct physical path.

`python scripts/build_static.py` builds the generated `public/` folder for Vercel. The root `build_static.py` remains a compatibility entry point. Never edit generated files. Static publication is allowlisted; tests, documentation, credentials and databases must not be added to it.

Run all frontend tests with `node scripts/test_frontend.cjs`. Tests in `tests/frontend/` read physical source through `helpers/project.cjs`; runtime modules are required using explicit repository-relative paths. Tests do not monkeypatch the filesystem.

Run all backend tests with `python scripts/test_backend.py`, or selected modules with `python scripts/test_backend.py test_accounting test_hosted_assets`. The runner discovers both `test_*.py` and feature `*_test.py` files. Its test process has no hosted database or exchange encryption credentials and permits loopback connections only. A real OS sandbox is still needed for strict security isolation.

Local ignored files, including `portfolio.sqlite3`, `.env*`, `.venv`, `.vercel`, `.pg-test`, recovery copies and user-installed agent tooling, remain where they were. Do not relocate or delete live data as part of source organization.
