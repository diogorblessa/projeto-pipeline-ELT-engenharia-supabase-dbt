# ---------- builder ----------
FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
COPY extract_load/pyproject.toml extract_load/
COPY transform/pyproject.toml transform/
COPY .llm/case-01-dashboard/pyproject.toml .llm/case-01-dashboard/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package transform

COPY transform/ transform/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package transform

# ---------- runtime ----------
FROM python:3.11-slim AS runtime

WORKDIR /app/transform
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DBT_PROFILES_DIR=/app/transform \
    DBT_PROJECT_DIR=/app/transform

RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

ENTRYPOINT ["dbt"]
CMD ["--help"]
