"""RAG document source connectors.

Provides integrations for fetching documents from external sources
(Google Drive, S3) for ingestion into the RAG pipeline.
"""

from app.services.rag.sources.s3 import S3Source

__all__ = [
    "S3Source",
]
