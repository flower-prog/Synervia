
# Build stage
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_HTTP_TIMEOUT=300

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the application together with the pre-downloaded local embedding model.
COPY . /app
RUN echo "1294ea4b6331115a353d81f96b85e8c8d7fdcc284453d5b2fab5b016230aad38  /app/models_cache/fast-bge-small-zh-v1.5/model_optimized.onnx" \
    | sha256sum --check -

# Install project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# Runtime stage
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

# Add venv to path
ENV PATH="/app/.venv/bin:$PATH"

# Create non-root user and writable directories
RUN adduser --disabled-password --gecos "" appuser && \
    mkdir -p /app/media /app/data /app/chroma_data /app/models_cache && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["python", "-m", "cli.commands", "server", "run", "--host", "0.0.0.0", "--port", "8000"]
