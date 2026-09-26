# Troubleshooting

## `ModuleNotFoundError: No module named 'luna_shared'`

The workspace packages are not on the path. Re-run the bootstrap script, which
writes a `sitecustomize.py` into the virtualenv:

```bash
uv run python scripts/bootstrap.py
```

This is required once after creating or recreating the `.venv`.

## `sqlalchemy.exc.MissingGreenlet`

The async SQLAlchemy bridge needs `greenlet`, and connections must not be shared
across event loops. It is already a dependency; if you see this, run
`uv sync --group dev`. For local runs, file-backed SQLite uses `NullPool` to
avoid cross-loop connection reuse.

## Search returns no results

- Confirm data is loaded: `GET /api/v1/admin/index/stats` should show non-zero
  documents/postings/terms. If empty, run `scripts/seed_demo_data.py` or a crawl.
- After crawling, make sure the indexer processed the queue and that you ran
  `compute_pagerank.py` if you rely on authority ordering.

## Admin login fails

- Seed demo users first (`scripts/seed_demo_data.py`) — default is
  `admin@nexussearch.dev / admin123`.
- A `401` with "Invalid credentials" is intentional and does not reveal whether
  the account exists.

## `403 Forbidden` on an admin action

Your role lacks the permission. `viewer` is read-only, `operator` can manage
crawls/settings, `admin` can do everything (users, API keys, audit).

## Docker services restart or never become healthy

- Check the `migrate` container completed: app services depend on it.
- Verify `postgres`, `redis`, `rabbitmq` are healthy (`docker compose ps`).
- Look at logs: `docker compose logs <service>`.

## Frontend can't reach the API

- Local dev: Vite proxies `/api` to `http://localhost:8000` — make sure the
  gateway is running (`scripts/run_local.py`).
- Docker: nginx proxies `/api` to `api-gateway:8000` (see `frontend/nginx.conf`).
- Check `VITE_API_URL` if you call the API by absolute URL.

## Tests fail after adding a new shared subpackage

The editable finder caches submodules. Re-run:

```bash
uv run python scripts/bootstrap.py
```

## Production startup refuses to boot

In `ENVIRONMENT=production`, the services reject a placeholder `JWT_SECRET`.
Set a strong secret. Other invalid config (bad URLs, out-of-range values) also
fails fast by design.
