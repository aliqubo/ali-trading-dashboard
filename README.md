# Ali Trading Dashboard

Enterprise Trading Platform.

> **Phase status:** Core Infrastructure. This phase provides the runnable
> project skeleton only — no business logic, no domain models, no trading, AI,
> indicators or risk. The only HTTP endpoints exposed are `/`, `/health`,
> `/health/live`, `/health/ready` and `/version`.

## Reference documents (frozen)

The architecture is governed by four approved, frozen documents. No code may
deviate from them:

- `ARCHITECTURE.md` v1.1.0
- `DATABASE_DESIGN.md` v1.0.0
- `BACKEND_SPECIFICATION.md` v1.0.0
- `SYSTEM_DESIGN.md` v1.0.0

## Tech stack (this phase)

- Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic
- PostgreSQL, Redis
- Docker, Docker Compose, GitHub Actions

## Quick start

```bash
# 1. Copy the environment template
cp .env.example .env

# 2. Bring everything up
docker compose up --build
```

The backend will be available at `http://localhost:8000`.

### Verify health

```bash
curl http://localhost:8000/            # service identity
curl http://localhost:8000/version     # version + environment
curl http://localhost:8000/health/live # liveness
curl http://localhost:8000/health/ready# readiness (checks DB + Redis)
curl http://localhost:8000/health      # overall health
```

Interactive API docs: `http://localhost:8000/docs`.

## Development

```bash
# Hot-reload dev environment (exposes DB/Redis ports locally)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Local tooling

```bash
cd backend
pip install -r requirements-dev.txt

make test        # run the test suite with coverage
make lint        # ruff lint
make format      # ruff format
make type        # mypy
```

## Project layout

```
ali-trading-dashboard/
├── backend/            FastAPI service (Core Infrastructure)
│   ├── app/
│   │   ├── core/       config, logging, context, exceptions
│   │   ├── api/        deps + v1 router + infrastructure endpoints
│   │   ├── db/         async engine/session + health probe
│   │   ├── cache/      Redis client + health probe
│   │   ├── schemas/    system response contracts
│   │   ├── middleware/ request id + request logging
│   │   └── main.py     application factory
│   ├── alembic/        migration configuration only (no migrations yet)
│   └── tests/          unit + integration tests
├── deploy/nginx/       reverse proxy config
├── .github/workflows/  CI pipeline
├── docker-compose.yml
└── docker-compose.dev.yml
```

## Migrations

Alembic is configured but no migrations exist in this phase. The model layer and
initial migration are introduced in a later phase, strictly following
`DATABASE_DESIGN.md`.
