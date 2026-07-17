# CODEX.md

Repository context for Codex. Codex automatically loads `AGENTS.md`; this file adds
Synervia-specific navigation and execution priorities. If instructions conflict,
`AGENTS.md` and the nearest nested `AGENTS.md` take precedence.

## Repository Purpose

This repository now contains two distinct codebases:

| Path | Role | Change When |
|---|---|---|
| `product/synervia/` | Primary Synervia product code | Implementing product features and fixes |
| `fastapi_gen/` and `template/` | Retained upstream project generator | Changing generation behavior or backporting a generic fix |

Synervia is an enterprise AI assistant for permission-aware knowledge retrieval and
governed business actions. The product plan is maintained in `SYNERVIA_PLAN.md`.

## Source Of Truth

- Product requirements and current phase: `SYNERVIA_PLAN.md`
- Runtime product code: `product/synervia/`
- Initial fixed generation profile: `fastapi_gen/product_profiles.py`
- Generic generator template: `template/`

Do not regenerate over `product/synervia`. Generation checks must use a temporary output
directory. Product changes should be made directly in `product/synervia`; backport them to
the generic template only when they are genuinely reusable.

When working below `product/synervia`, also follow `product/synervia/AGENTS.md`.

## Current Priorities

The project is finishing Phase 0 and then proceeds through Phase 1 in this order:

1. Establish a versioned product baseline, make it reproducibly runnable, and add product CI.
2. Fix RAG ingestion status, retry semantics, chunk counts, and temporary-file cleanup.
3. Enforce organization and knowledge-base isolation across API, Agent, Worker, and pgvector.
4. Add reliable retrieval thresholds, reranking, no-evidence behavior, and traceable citations.
5. Add end-to-end RAG tests and a minimal evaluation set.

Do not expand multi-agent behavior, add many SaaS integrations, or allow unapproved write
actions before Phase 1 isolation and correctness checks pass.

## Product Commands

Run these from `product/synervia`:

```bash
make install       # Install backend development dependencies
make lint          # Backend lint, formatting check, and type check
make test          # Backend tests
make bootstrap     # Start the development stack, migrate, and seed an admin
make dev           # Start or restart the backend development stack
make dev-frontend  # Start the frontend container
```

For local frontend development:

```bash
cd product/synervia/frontend
bun install
bun run lint
bun run type-check
bun run test:run
bun run build
bun run dev
```

Root generator checks remain available for changes under `fastapi_gen/`, `template/`,
`scripts/`, or root `tests/`:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format . --check
uv run ty check
```

## Product Architecture

```text
product/synervia/
|- backend/
|  |- app/api/           FastAPI routes and request dependencies
|  |- app/services/      Business rules and orchestration
|  |- app/repositories/  Database access
|  |- app/db/models/     SQLAlchemy models
|  |- app/agents/        PydanticAI assistant and tools
|  |- app/services/rag/  Parsing, embeddings, retrieval, and pgvector
|  `- app/worker/        Celery tasks
|- frontend/             Next.js 15 application
`- docker-compose*.yml   Development, staging, and production stacks
```

Important product boundaries:

- Routes delegate business behavior to services.
- Repositories flush database changes; transaction ownership remains outside repositories.
- Knowledge-base and tool authorization must be enforced by server-side code, never prompts.
- Agent-provided collection names, resource IDs, and permissions are untrusted input.
- Asynchronous workflows require explicit states, idempotency, retry behavior, and recovery.
- Write tools must go through permission checks, approval when required, and audit logging.

## Working Rules

- Check `git status` before editing; preserve unrelated and untracked user work.
- Scope product changes to `product/synervia` unless the task explicitly concerns generation.
- Add database migrations for model changes.
- Add focused tests for authorization, state transitions, retries, and failure recovery.
- For frontend changes, verify desktop and mobile behavior as well as lint and type checks.
- Never use `make docker-clean` unless the user explicitly authorizes deleting local data.

## References

- Product and implementation plan: `SYNERVIA_PLAN.md`
- Product setup: `product/synervia/README.md`
- Product environment variables: `product/synervia/ENV_VARS.md`
- Product architecture: `product/synervia/docs/architecture.md`
- Generator variables: `template/cookiecutter.json`
- Generator cleanup hook: `template/hooks/post_gen_project.py`
