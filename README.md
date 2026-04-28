# Pipeline ELT — E-commerce Analytics

Pipeline ELT com extração Python (S3 → PostgreSQL) e transformação dbt
(Bronze → Silver → Gold) sobre Supabase.

## Stack

- Python 3.11 + uv (dependency manager)
- boto3, pandas, sqlalchemy, psycopg2 (`extract_load/`)
- dbt-core, dbt-postgres (`transform/`)
- Docker + docker-compose
- ruff (lint+format), pytest (testes)

## Estrutura

- `extract_load/` — etapas Extract + Load (S3 → Postgres `public`)
- `transform/` — projeto dbt (Bronze → Silver → Gold)

## Setup local

```bash
# 1. Apagar venv antiga (se existir)
rm -rf .venv

# 2. Instalar deps com uv
uv sync --all-packages

# 3. Configurar segredos
cp .env.example .env
# editar .env com valores reais (ver comentarios no .env.example)
```

## Rodar pipeline (host)

```bash
# Extract + Load
uv run --package extract_load python -m extract_load

# Transform
uv run --package transform dbt run --project-dir transform --profiles-dir transform

# Testes Python
uv run pytest

# Lint
uv run ruff check
uv run ruff format
```

## Rodar pipeline (Docker)

```bash
docker compose build
docker compose run --rm extract
docker compose run --rm dbt run
docker compose run --rm dbt test
```

## Segurança

- **Nunca commite o `.env`** — está no `.gitignore`.
- Ao rotacionar credenciais no Supabase, atualize o `.env` local apenas.
- Se um segredo vazar: rotacione imediatamente, **mesmo após `git rm --cached`**
  (push não desfaz vazamento — a credencial já foi exposta).

## Documentação adicional

- Arquitetura detalhada: `CLAUDE.md`
- Modelos dbt: `transform/PRD-dbt.md`
- Schemas Gold: `.llm/database.md`
