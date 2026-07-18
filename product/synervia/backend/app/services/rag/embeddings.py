from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from openai import OpenAI

from app.core.config import settings as app_settings
from app.services.rag.config import RAGSettings
from app.services.rag.models import Document

if TYPE_CHECKING:
    from fastembed import TextEmbedding


def _chunk_texts(document: Document) -> list[str]:
    return [
        doc.chunk_content if doc.chunk_content else "" for doc in (document.chunked_pages or [])
    ]


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        pass

    @abstractmethod
    def embed_document(self, document: Document) -> list[list[float]]:
        pass

    @abstractmethod
    def warmup(self) -> None:
        """Ensures the model is loaded and ready for inference."""
        pass


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider using the OpenAI API.

    Uses OpenAI's embedding models to generate text embeddings.
    """

    def __init__(self, model: str, api_key: str = "", base_url: str | None = None) -> None:
        """Initialize the OpenAI embedding provider.

        Args:
            model: The OpenAI embedding model name (e.g., 'text-embedding-3-small').
            api_key: API key; falls back to OPENAI_API_KEY env var when empty.
            base_url: Override base URL (e.g. OpenRouter-compatible endpoint).
        """
        self.model = model
        self.client = OpenAI(api_key=api_key or None, base_url=base_url)

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [data.embedding for data in response.data]

    def embed_document(self, document: Document) -> list[list[float]]:
        return self.embed_queries(_chunk_texts(document))

    def warmup(self) -> None:
        pass


def _load_text_embedding(model: str, cache_dir: Path) -> TextEmbedding:
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=model, cache_dir=str(cache_dir))


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """CPU embedding provider backed by FastEmbed's ONNX runtime."""

    def __init__(self, model: str, cache_dir: Path) -> None:
        self.model = model
        self.cache_dir = cache_dir
        self._embedding_model: TextEmbedding | None = None

    @property
    def embedding_model(self) -> TextEmbedding:
        if self._embedding_model is None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._embedding_model = _load_text_embedding(self.model, self.cache_dir)
        return self._embedding_model

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self.embedding_model.query_embed(texts)]

    def embed_document(self, document: Document) -> list[list[float]]:
        return [
            vector.tolist() for vector in self.embedding_model.passage_embed(_chunk_texts(document))
        ]

    def warmup(self) -> None:
        _ = self.embedding_model


class EmbeddingService:
    def __init__(self, settings: RAGSettings):
        config = settings.embeddings_config
        self.expected_dim = config.dim
        provider = app_settings.EMBEDDING_PROVIDER
        if provider == "local":
            self.provider = LocalEmbeddingProvider(
                model=config.model,
                cache_dir=app_settings.MODELS_CACHE_DIR,
            )
            return
        if provider == "openrouter":
            api_key = app_settings.EMBEDDING_API_KEY or app_settings.OPENROUTER_API_KEY
            base_url = app_settings.EMBEDDING_BASE_URL or "https://openrouter.ai/api/v1"
        else:
            api_key = app_settings.EMBEDDING_API_KEY or app_settings.OPENAI_API_KEY
            base_url = app_settings.EMBEDDING_BASE_URL or app_settings.OPENAI_BASE_URL
        self.provider = OpenAIEmbeddingProvider(
            model=config.model,
            api_key=api_key,
            base_url=base_url,
        )

    def embed_query(self, query: str) -> list[float]:
        result = self.provider.embed_queries([query])[0]
        if len(result) != self.expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.expected_dim}, "
                f"got {len(result)}. Check your embedding model configuration."
            )
        return result

    def embed_document(self, document: Document) -> list[list[float]]:
        results = self.provider.embed_document(document)
        if results and len(results[0]) != self.expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.expected_dim}, "
                f"got {len(results[0])}. Check your embedding model configuration."
            )
        return results

    def warmup(self) -> None:
        self.provider.warmup()
