#!/usr/bin/env python3
"""Download and verify the default FastEmbed model without project dependencies."""

from __future__ import annotations

import hashlib
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://storage.googleapis.com/qdrant-fastembed/"
    "fast-bge-small-zh-v1.5.tar.gz"
)
ARCHIVE_SHA256 = "bf023219b6029148fddf764d248808816c0ca1f107f058231bb1ae0fa526f83f"
MODEL_SHA256 = "1294ea4b6331115a353d81f96b85e8c8d7fdcc284453d5b2fab5b016230aad38"
MODEL_DIR_NAME = "fast-bge-small-zh-v1.5"
MODEL_FILE = "model_optimized.onnx"
REQUIRED_FILES = {
    "config.json",
    MODEL_FILE,
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_ready(model_dir: Path) -> bool:
    if not all((model_dir / name).is_file() for name in REQUIRED_FILES):
        return False
    return _sha256(model_dir / MODEL_FILE) == MODEL_SHA256


def download_model() -> None:
    cache_dir = Path(__file__).resolve().parents[1] / "models_cache"
    model_dir = cache_dir / MODEL_DIR_NAME
    if _is_ready(model_dir):
        print(f"Embedding model ready: {model_dir}")
        return

    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".fastembed-", dir=cache_dir) as temp:
        temp_dir = Path(temp)
        archive = temp_dir / "model.tar.gz"
        extract_dir = temp_dir / "extract"
        extract_dir.mkdir()

        print(f"Downloading embedding model from {MODEL_URL}")
        with urllib.request.urlopen(MODEL_URL, timeout=300) as response:
            with archive.open("wb") as output:
                shutil.copyfileobj(response, output)

        digest = _sha256(archive)
        if digest != ARCHIVE_SHA256:
            raise RuntimeError(f"Embedding model archive checksum mismatch: {digest}")

        with tarfile.open(archive, "r:gz") as bundle:
            bundle.extractall(extract_dir, filter="data")

        extracted_model = extract_dir / MODEL_DIR_NAME
        if not _is_ready(extracted_model):
            raise RuntimeError(f"Embedding model is incomplete: {extracted_model}")

        if model_dir.exists():
            shutil.rmtree(model_dir)
        extracted_model.rename(model_dir)

    print(f"Embedding model downloaded and verified: {model_dir}")


if __name__ == "__main__":
    download_model()
