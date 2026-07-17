"""Deterministic product profiles built from the generic project template."""

from .config import (
    AIFrameworkType,
    BackgroundTaskType,
    BrandColorType,
    CIType,
    FrontendType,
    LLMProviderType,
    LogfireFeatures,
    PdfParserType,
    ProjectConfig,
    RAGFeatures,
    RateLimitStorageType,
    RerankerType,
    TenancyMode,
    VectorStoreType,
)


def get_synervia_config() -> ProjectConfig:
    """Return the fixed configuration used to bootstrap the Synervia product."""
    return ProjectConfig(
        project_name="synervia",
        project_description=(
            "An enterprise AI assistant for secure knowledge access and governed actions"
        ),
        author_name="Synervia",
        author_email="engineering@example.com",
        background_tasks=BackgroundTaskType.CELERY,
        enable_redis=True,
        enable_caching=True,
        enable_rate_limiting=True,
        rate_limit_storage=RateLimitStorageType.REDIS,
        enable_admin_panel=True,
        enable_websockets=True,
        enable_file_storage=True,
        enable_webhooks=True,
        enable_sentry=True,
        enable_prometheus=True,
        ai_framework=AIFrameworkType.PYDANTIC_AI,
        llm_provider=LLMProviderType.ALL,
        enable_web_search=True,
        enable_web_fetch=True,
        enable_charts=True,
        enable_skills=True,
        enable_teams=True,
        tenancy=TenancyMode.MULTI_ORG,
        enable_per_org_quotas=True,
        enable_billing=False,
        enable_credits_system=False,
        enable_usage_dashboard=False,
        enable_admin_features_subscriptions=False,
        enable_admin_features_stripe_events=False,
        frontend=FrontendType.NEXTJS,
        brand_color=BrandColorType.GREEN,
        enable_brand_from_config=True,
        enable_marketing_site=False,
        enable_docker=True,
        enable_kubernetes=False,
        ci_type=CIType.GITHUB,
        enable_logfire=True,
        logfire_features=LogfireFeatures(
            fastapi=True,
            database=True,
            redis=True,
            celery=True,
            httpx=True,
        ),
        rag_features=RAGFeatures(
            enable_rag=True,
            enable_s3_ingestion=True,
            reranker_type=RerankerType.NONE,
            enable_image_description=False,
            pdf_parser=PdfParserType.PYMUPDF,
            vector_store=VectorStoreType.PGVECTOR,
        ),
    )


__all__ = ["get_synervia_config"]
