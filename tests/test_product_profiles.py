"""Tests for fixed product profiles maintained by this repository."""

from pathlib import Path

from fastapi_gen.generator import generate_project
from fastapi_gen.product_profiles import get_synervia_config


def test_synervia_profile_has_enterprise_ai_baseline() -> None:
    context = get_synervia_config().to_cookiecutter_context()

    assert context["project_slug"] == "synervia"
    assert context["use_pydantic_ai"] is True
    assert context["use_all_providers"] is True
    assert context["use_nextjs"] is True
    assert context["enable_teams"] is True
    assert context["tenancy"] == "multi_org"
    assert context["enable_rag"] is True
    assert context["use_pgvector"] is True
    assert context["use_celery"] is True
    assert context["enable_redis"] is True
    assert context["enable_billing"] is False


def test_synervia_profile_enables_governance_foundations() -> None:
    context = get_synervia_config().to_cookiecutter_context()

    assert context["enable_admin_panel"] is True
    assert context["enable_admin_features_audit_log"] is True
    assert context["enable_per_org_quotas"] is True
    assert context["enable_rate_limiting"] is True
    assert context["rate_limit_storage_redis"] is True
    assert context["enable_webhooks"] is True
    assert context["enable_sentry"] is True
    assert context["enable_prometheus"] is True


def test_synervia_profile_generates_concrete_product(
    tmp_path: Path,
    monkeypatch,
) -> None:
    # Cookiecutter's post-generation hook opportunistically runs uv/uvx/npx.
    # Generation tests must stay deterministic and must not access the network.
    monkeypatch.setenv("PATH", "")

    project = generate_project(get_synervia_config(), tmp_path)

    assert (project / "backend" / "app" / "agents" / "assistant.py").is_file()
    assert (project / "backend" / "app" / "agents" / "tools" / "rag_tool.py").is_file()
    assert (project / "backend" / "app" / "services" / "rag" / "vectorstore.py").is_file()
    assert (project / "backend" / "app" / "worker" / "celery_app.py").is_file()
    assert (project / "frontend" / "package.json").is_file()

    assert not (project / "backend" / "app" / "agents" / "langchain_assistant.py").exists()
    assert not (project / "backend" / "app" / "agents" / "deepagents_assistant.py").exists()

    backend_config = (project / "backend" / "app" / "core" / "config.py").read_text()
    assert "cookiecutter" not in backend_config
