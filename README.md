# EM CONSTRUÇÃO - Ainda vou adicionar alguns prints, diagrama do pipeline e outros dados

# Pipeline ELT — E-commerce Analytics

Pipeline ELT com extracao Python (S3 -> PostgreSQL) e transformacao dbt
(Bronze -> Silver conformada -> Gold dimensional -> Gold marts) sobre Supabase.

## Stack

- Python 3.11 + uv (dependency manager)
- boto3, pandas, sqlalchemy, psycopg2 (`extract_load/`)
- dbt-core, dbt-postgres (`transform/`)
- Docker + docker-compose
- ruff (lint+format), pytest (testes)

## Estrutura

- `extract_load/` - etapas Extract + Load (S3 -> Postgres `public`)
- `transform/` - projeto dbt (Bronze -> Silver conformada -> Gold dimensional -> Gold marts)

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

**Pipeline completo (recomendado):**

```bash
./scripts/run-pipeline.sh
```

Roda Extract+Load e dbt run em sequencia. Use este atalho no dia a dia: EL e T precisam rodar juntos porque o EL faz `DROP CASCADE` nas raw (apaga as views bronze) e o dbt run logo depois reconstroi a cadeia bronze -> silver -> gold.

## Modelos analiticos

- Silver: camada conformada, responsavel por tipos, deduplicacao, padronizacao textual, regras de nulos e produtos inferidos quando fatos referenciam produtos ausentes no catalogo.
- Gold dimensional: `public_gold.gold_dim_*` e `public_gold.gold_fct_*`.
- Marts finais:
  - `public_gold_sales.gold_sales_vendas_temporais`
  - `public_gold_cs.gold_customer_success_clientes_segmentacao`
  - `public_gold_pricing.gold_pricing_precos_competitividade`

**Etapas separadas (para debug ou runs seletivos):**

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
