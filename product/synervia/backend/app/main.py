# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals
"""FastAPI application entry point."""

import logging
import secrets
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from typing import TypedDict

from fastapi import FastAPI
from fastapi import Depends, Header, HTTPException, status as http_status
from fastapi_pagination import add_pagination
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.exception_handlers import register_exception_handlers
from app.api.router import api_router
from app.core.config import settings
from app.db.session import close_db
from app.core.logfire_setup import instrument_app, setup_logfire
from app.core.logfire_setup import instrument_asyncpg
from app.core.logfire_setup import instrument_redis
from app.core.logfire_setup import instrument_httpx
from app.core.logfire_setup import instrument_pydantic_ai
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware
from app.core.cache import setup_cache
from app.clients.redis import RedisClient
from app.services.rag.embeddings import EmbeddingService
from app.services.rag.vectorstore import PgVectorStore
from app.services.rag.vectorstore import BaseVectorStore
from app.admin import setup_admin
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)


class LifespanState(TypedDict, total=False):
    """Lifespan state - resources available via request.state."""

    redis: RedisClient
    embedding_service: EmbeddingService
    vector_store: BaseVectorStore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[LifespanState, None]:
    """Application lifespan - startup and shutdown events.

    Resources yielded here are available via request.state in route handlers.
    See: https://asgi.readthedocs.io/en/latest/specs/lifespan.html#lifespan-state
    """
    state: LifespanState = {}
    setup_logfire()
    instrument_asyncpg()
    instrument_redis()
    instrument_httpx()
    instrument_pydantic_ai()
    redis_client = RedisClient()
    await redis_client.connect()
    state["redis"] = redis_client
    setup_cache(redis_client)
    embedder: EmbeddingService | None = None
    try:
        embedder = EmbeddingService(settings=settings.rag)
        embedder.warmup()
        state["embedding_service"] = embedder
    except Exception as e:
        logger.error("Embedding service warmup failed: %s. RAG will not be available.", e)
    if embedder is not None:
        try:
            vector_store = PgVectorStore(settings=settings.rag, embedding_service=embedder)
            state["vector_store"] = vector_store
        except Exception as e:
            logger.error("pgvector connection failed: %s. Vector store will not be available.", e)
    yield state
    if "vector_store" in state:
        with suppress(Exception):
            await state["vector_store"].engine.dispose()  # type: ignore[attr-defined]
    if "redis" in state:
        await state["redis"].close()

    await close_db()


SHOW_DOCS_ENVIRONMENTS = ("local", "staging", "development")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    show_docs = settings.ENVIRONMENT in SHOW_DOCS_ENVIRONMENTS
    openapi_url = f"{settings.API_V1_STR}/openapi.json" if show_docs else None
    docs_url = "/docs" if show_docs else None
    redoc_url = "/redoc" if show_docs else None

    openapi_tags = [
        {
            "name": "health",
            "description": "Health check endpoints for monitoring and Kubernetes probes",
        },
        {
            "name": "auth",
            "description": "Authentication endpoints - login, register, token refresh",
        },
        {
            "name": "users",
            "description": "User management endpoints",
        },
        {
            "name": "conversations",
            "description": "AI conversation persistence - manage chat history",
        },
        {
            "name": "webhooks",
            "description": "Webhook management - subscribe to events and manage deliveries",
        },
        {
            "name": "agent",
            "description": "AI agent WebSocket endpoint for real-time chat",
        },
        {
            "name": "websocket",
            "description": "WebSocket endpoints for real-time communication",
        },
        {
            "name": "rag",
            "description": "Retrieval Augmented Generation endpoints",
        },
    ]

    setup_logging()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        summary="FastAPI application with Logfire observability",
        description="""
An enterprise AI assistant for secure knowledge access and governed actions

## Features
- **Authentication**: JWT-based authentication with refresh tokens
- **API Key**: Header-based API key authentication
- **Database**: Async database operations
- **Redis**: Caching and session storage
- **Rate Limiting**: Request rate limiting per client
- **AI Agent**: PydanticAI-powered conversational assistant
- **Observability**: Logfire integration for tracing and monitoring
- **RAG**: Retrieval Augmented Generation with Milvus and LangChain

## Documentation

- [Swagger UI](/docs) - Interactive API documentation
- [ReDoc](/redoc) - Alternative documentation view
        """.strip(),
        version="0.1.0",
        openapi_url=openapi_url,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_tags=openapi_tags,
        contact={"name": "Synervia"},
        license_info={
            "name": "MIT",
            "identifier": "MIT",
        },
        lifespan=lifespan,
    )
    # setup_logfire() is also called from the lifespan for the runtime app, but
    # we call it here too so that import-time test clients (which never run
    # lifespan) silence the "configure first" warning. setup_logfire() is
    # idempotent via a module-level guard in logfire_setup.py.
    setup_logfire()
    instrument_app(app)

    app.add_middleware(RequestIDMiddleware)

    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    if settings.SENTRY_DSN:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.SENTRY_DSN, enable_tracing=True)

    from prometheus_fastapi_instrumentator import Instrumentator

    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=[
            "/health",
            "/health/ready",
            "/health/live",
            settings.PROMETHEUS_METRICS_PATH,
        ],
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )
    instrumentator.instrument(app)
    # Optional Bearer-token guard so the metrics endpoint can be exposed on a
    # public ingress without leaking internals. When PROMETHEUS_AUTH_TOKEN is
    # empty the endpoint is unauthenticated (typical for private networks).
    if settings.PROMETHEUS_AUTH_TOKEN:

        def _verify_metrics_token(authorization: str = Header(default="")) -> None:
            expected = f"Bearer {settings.PROMETHEUS_AUTH_TOKEN}"
            if not secrets.compare_digest(authorization, expected):
                raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED)

        instrumentator.expose(
            app,
            endpoint=settings.PROMETHEUS_METRICS_PATH,
            include_in_schema=settings.PROMETHEUS_INCLUDE_IN_SCHEMA,
            dependencies=[Depends(_verify_metrics_token)],
        )
    else:
        instrumentator.expose(
            app,
            endpoint=settings.PROMETHEUS_METRICS_PATH,
            include_in_schema=settings.PROMETHEUS_INCLUDE_IN_SCHEMA,
        )

    # slowapi requires app.state.limiter, not lifespan state (library constraint)
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
    ADMIN_ALLOWED_ENVIRONMENTS = ["development", "local", "staging"]

    if settings.ENVIRONMENT in ADMIN_ALLOWED_ENVIRONMENTS:
        setup_admin(app)

    app.include_router(api_router, prefix=settings.API_V1_STR)

    add_pagination(app)

    return app


app = create_app()
