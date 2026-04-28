# ---------- builder ----------
FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Metadata do workspace (raiz + ambos pacotes)
COPY pyproject.toml uv.lock .python-version ./
COPY extract_load/pyproject.toml extract_load/
COPY transform/pyproject.toml transform/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package extract_load

COPY extract_load/src extract_load/src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package extract_load

# ---------- runtime ----------
FROM python:3.11-slim AS runtime

WORKDIR /app
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

ENTRYPOINT ["python", "-m", "extract_load"]
