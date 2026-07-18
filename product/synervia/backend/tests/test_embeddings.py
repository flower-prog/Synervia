"""Tests for embedding provider routing and dimension validation."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.config import settings as app_settings
from app.services.rag.config import EmbeddingsConfig, RAGSettings
from app.services.rag.embeddings import (
    EmbeddingService,
    LocalEmbeddingProvider,
    _load_text_embedding,
)


class TestEmbeddingConfiguration:
    def test_provider_prefixed_openai_model_resolves_dimension(self):
        config = EmbeddingsConfig(model="openai/text-embedding-3-small")

        assert config.dim == 1536

    def test_free_openrouter_model_resolves_dimension(self):
        config = EmbeddingsConfig(model="nvidia/llama-nemotron-embed-vl-1b-v2:free")

        assert config.dim == 2048

    def test_local_chinese_model_resolves_dimension(self):
        config = EmbeddingsConfig(model="BAAI/bge-small-zh-v1.5")

        assert config.dim == 512

    def test_unknown_model_requires_explicit_dimension(self):
        with pytest.raises(ValueError, match="set EMBEDDING_DIMENSIONS explicitly"):
            EmbeddingsConfig(model="vendor/unknown-embedding-model")

    def test_unknown_model_accepts_explicit_dimension(self):
        config = EmbeddingsConfig(model="vendor/unknown-embedding-model", dim=768)

        assert config.dim == 768


class TestEmbeddingProviderRouting:
    def test_local_provider_uses_model_cache(self, tmp_path: Path):
        rag_settings = RAGSettings(
            embeddings_config=EmbeddingsConfig(model="BAAI/bge-small-zh-v1.5")
        )
        with (
            patch.object(app_settings, "EMBEDDING_PROVIDER", "local"),
            patch.object(app_settings, "MODELS_CACHE_DIR", tmp_path),
            patch("app.services.rag.embeddings.LocalEmbeddingProvider") as provider_cls,
        ):
            service = EmbeddingService(rag_settings)

        provider_cls.assert_called_once_with(
            model="BAAI/bge-small-zh-v1.5",
            cache_dir=tmp_path,
        )
        assert service.provider is provider_cls.return_value

    def test_openai_provider_reuses_openai_compatible_gateway(self):
        rag_settings = RAGSettings(
            embeddings_config=EmbeddingsConfig(model="text-embedding-3-small")
        )
        with (
            patch.object(app_settings, "EMBEDDING_PROVIDER", "openai"),
            patch.object(app_settings, "EMBEDDING_API_KEY", ""),
            patch.object(app_settings, "EMBEDDING_BASE_URL", None),
            patch.object(app_settings, "OPENAI_API_KEY", "relay-key"),
            patch.object(app_settings, "OPENAI_BASE_URL", "https://relay.example/v1"),
            patch("app.services.rag.embeddings.OpenAIEmbeddingProvider") as provider_cls,
        ):
            service = EmbeddingService(rag_settings)

        provider_cls.assert_called_once_with(
            model="text-embedding-3-small",
            api_key="relay-key",
            base_url="https://relay.example/v1",
        )
        assert service.provider is provider_cls.return_value

    def test_embedding_overrides_take_precedence(self):
        rag_settings = RAGSettings(
            embeddings_config=EmbeddingsConfig(model="vendor/custom-embed", dim=768)
        )
        with (
            patch.object(app_settings, "EMBEDDING_PROVIDER", "openai"),
            patch.object(app_settings, "EMBEDDING_API_KEY", "embedding-key"),
            patch.object(app_settings, "EMBEDDING_BASE_URL", "https://embeddings.example/v1"),
            patch.object(app_settings, "OPENAI_API_KEY", "chat-key"),
            patch.object(app_settings, "OPENAI_BASE_URL", "https://chat.example/v1"),
            patch("app.services.rag.embeddings.OpenAIEmbeddingProvider") as provider_cls,
        ):
            EmbeddingService(rag_settings)

        provider_cls.assert_called_once_with(
            model="vendor/custom-embed",
            api_key="embedding-key",
            base_url="https://embeddings.example/v1",
        )

    def test_openrouter_provider_uses_openrouter_defaults(self):
        rag_settings = RAGSettings(
            embeddings_config=EmbeddingsConfig(model="nvidia/llama-nemotron-embed-vl-1b-v2:free")
        )
        with (
            patch.object(app_settings, "EMBEDDING_PROVIDER", "openrouter"),
            patch.object(app_settings, "EMBEDDING_API_KEY", ""),
            patch.object(app_settings, "EMBEDDING_BASE_URL", None),
            patch.object(app_settings, "OPENROUTER_API_KEY", "openrouter-key"),
            patch("app.services.rag.embeddings.OpenAIEmbeddingProvider") as provider_cls,
        ):
            EmbeddingService(rag_settings)

        provider_cls.assert_called_once_with(
            model="nvidia/llama-nemotron-embed-vl-1b-v2:free",
            api_key="openrouter-key",
            base_url="https://openrouter.ai/api/v1",
        )


class _FakeVector:
    def __init__(self, values: list[float]) -> None:
        self.values = values

    def tolist(self) -> list[float]:
        return self.values


def test_local_provider_uses_retrieval_specific_embedding_methods(tmp_path: Path):
    embedding_model = SimpleNamespace(
        query_embed=lambda texts: [_FakeVector([1.0, 2.0]) for _ in texts],
        passage_embed=lambda texts: [_FakeVector([3.0, 4.0]) for _ in texts],
    )
    with patch(
        "app.services.rag.embeddings._load_text_embedding", return_value=embedding_model
    ) as loader:
        provider = LocalEmbeddingProvider("BAAI/bge-small-zh-v1.5", tmp_path / "models")
        provider.warmup()

        query_vectors = provider.embed_queries(["查询"])
        document_vectors = provider.embed_document(
            SimpleNamespace(chunked_pages=[SimpleNamespace(chunk_content="文档")])  # type: ignore[arg-type]
        )

    loader.assert_called_once_with(
        "BAAI/bge-small-zh-v1.5",
        tmp_path / "models",
    )
    assert query_vectors == [[1.0, 2.0]]
    assert document_vectors == [[3.0, 4.0]]


def test_load_text_embedding_passes_model_and_cache_dir(tmp_path: Path):
    text_embedding = Mock()
    fastembed_module = SimpleNamespace(TextEmbedding=text_embedding)

    with patch.dict(sys.modules, {"fastembed": fastembed_module}):
        result = _load_text_embedding("BAAI/bge-small-zh-v1.5", tmp_path)

    text_embedding.assert_called_once_with(
        model_name="BAAI/bge-small-zh-v1.5",
        cache_dir=str(tmp_path),
    )
    assert result is text_embedding.return_value
