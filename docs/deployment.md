# Deployment

## Docker Compose (recommended)

```bash
cp .env.example .env
# Set a strong JWT_SECRET and passwords before any non-local use.
docker compose up --build
```

Compose starts:

- `postgres`, `redis`, `rabbitmq` with health checks
- `migrate` — a one-shot container that runs `alembic upgrade head` and exits
- the six application services (each waits for `migrate` to complete)
- `frontend` (nginx serving the built SPA, proxying `/api` to the gateway)

Seed demo data once services are healthy:

```bash
docker compose run --rm migrate python /app/scripts/seed_demo_data.py
```

Endpoints: gateway `:8000`, frontend `:3000`, and (for diagnostics) each
service on its port. In production, do not expose the individual service ports —
only the gateway and frontend.

## Configuration

All configuration is environment-driven (see `.env.example`). Precedence is
code defaults < YAML policy files (`config/crawler.yaml`, `config/ranking.yaml`)
< environment variables.

Key variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres DSN (or `sqlite+aiosqlite:///path` for local) |
| `REDIS_URL` | `redis://…` or `memory://` |
| `RABBITMQ_URL` | `amqp://…` or `memory://` |
| `JWT_SECRET` | Token signing secret — **must** be strong in production |
| `ENVIRONMENT` | `development` or `production` |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `RANKING_API_URL`, `SEARCH_API_URL`, `ADMIN_API_URL` | Service URLs |

In `production` mode the services refuse to start with a placeholder
`JWT_SECRET` (`config.Settings.validate_for_startup`).

## Migrations

The image bundles the migrations and Alembic config. To run manually:

```bash
DATABASE_URL=postgresql://user:pass@host:5432/db uv run python scripts/migrate.py
```

`migrate.py` waits for the database to accept connections, then applies
`alembic upgrade head`. It is safe to run repeatedly.

## Scaling notes

- The services are stateless; scale `search-api`, `crawler`, and `indexer`
  horizontally behind the gateway / queue.
- PostgreSQL is the source of truth. Redis may be lost without data loss (only
  cache and rate-limit state). RabbitMQ messages are acknowledged only after the
  durable side effect commits, and unprocessable messages are dead-lettered.
- Put TLS termination and edge policy (CORS, request size, security headers) at
  nginx / the gateway. `config/nginx.conf` is the frontend reverse proxy.

## Production checklist

- [ ] Strong `JWT_SECRET` and database/broker passwords
- [ ] `ENVIRONMENT=production`
- [ ] TLS in front of the gateway and frontend
- [ ] Individual service ports not publicly exposed
- [ ] Backups configured for PostgreSQL
- [ ] Log aggregation for the JSON logs each service emits
