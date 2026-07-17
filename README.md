# Synervia

Synervia is an enterprise AI assistant platform for secure knowledge access and governed
business actions. It connects employees with internal knowledge, business systems, and
workflows through one conversational interface while keeping permissions, approvals, and
auditability under server-side control.

The project is currently finishing its product baseline and beginning the enterprise RAG
correctness and tenant-isolation work described in [SYNERVIA_PLAN.md](SYNERVIA_PLAN.md).

## Product Goals

Synervia is designed around three capabilities:

- Understand the enterprise through permission-aware knowledge and business context.
- Complete work through controlled tools, connectors, and workflows.
- Remain governable through RBAC, tenant isolation, approvals, audit logs, quotas, and cost
  visibility.

It is not intended to be an unrestricted autonomous agent or a document-only chatbot.

## Current Baseline

The generated product baseline includes:

- FastAPI and Python 3.12 backend
- Next.js 15 frontend
- PydanticAI agent runtime with multiple model providers
- PostgreSQL and pgvector
- Redis and Celery background processing
- Organization, member, role, and knowledge-base models
- Document upload, ingestion, synchronization, retrieval, and citations
- S3/MinIO-compatible file storage
- Docker Compose development and deployment configurations
- Logfire, Prometheus, and Sentry integration points

These capabilities are being hardened before they are considered production-ready. In
particular, RAG task state, tenant isolation, retrieval quality, and governed tool execution
remain active implementation phases.

## Repository Layout

```text
synervia/
|- product/synervia/        Primary product code
|  |- backend/              FastAPI application, Agent, RAG, workers, and migrations
|  |- frontend/             Next.js application
|  `- docker-compose*.yml   Development, staging, and production stacks
|- fastapi_gen/             Retained upstream generator implementation
|- template/                Retained generic Cookiecutter template
|- scripts/                 Deterministic Synervia generation helper
|- tests/                   Generator profile tests
`- SYNERVIA_PLAN.md         Product and implementation plan
```

`product/synervia` is the product source of truth. Do not regenerate over it. The retained
generator exists to document the original baseline and to validate generation in temporary
directories.

## Quick Start

Prerequisites:

- Docker with Docker Compose
- GNU Make
- `uv`
- Bun when running the frontend outside Docker

Start the backend stack, apply migrations, and create the local development administrator:

```bash
cd product/synervia
cp backend/.env.example backend/.env
make bootstrap
```

Start the frontend in Docker:

```bash
make dev-frontend
```

Or run it locally:

```bash
cd frontend
bun install
bun run dev
```

Local services:

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| OpenAPI | http://localhost:8000/docs |
| Admin | http://localhost:8000/admin |

The development seed creates `admin@example.com` with password `admin123`. These credentials
are for local development only and must never be used in a deployed environment.

## Development

Run product backend checks from `product/synervia`:

```bash
make install
make lint
make test
```

Run frontend checks from `product/synervia/frontend`:

```bash
bun run lint
bun run type-check
bun run test:run
bun run build
```

Run retained generator checks from the repository root:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format . --check
uv run ty check
```

## Configuration

Development defaults live in `product/synervia/backend/.env.example`. Docker Compose requires
a local `backend/.env`, so copy the example before the first start. Keep real credentials out
of version control.

Important production settings include:

- JWT and API signing secrets
- PostgreSQL and Redis credentials
- LLM provider keys
- S3/MinIO credentials
- Sentry and Logfire configuration
- Explicit CORS origins

See [ENV_VARS.md](product/synervia/ENV_VARS.md) and
[MANUAL_STEPS.md](product/synervia/MANUAL_STEPS.md) for details.

## Architecture And Roadmap

- [Product and implementation plan](SYNERVIA_PLAN.md)
- [Product architecture](product/synervia/docs/architecture.md)
- [Product commands](product/synervia/docs/commands.md)
- [Deployment guide](product/synervia/docs/deploy.md)
- [Security policy](product/synervia/SECURITY.md)
- [Codex repository guide](CODEX.md)

## Upstream

Synervia was bootstrapped from version `0.2.15` of the
[Full-Stack AI Agent Template](https://github.com/vstorm-co/full-stack-ai-agent-template).
The upstream generator remains in this repository temporarily for reproducibility and
selective backports. Product development happens directly in `product/synervia`.

## License

This repository retains the upstream MIT license. See [LICENSE](LICENSE).
