# CLAUDE.md

Este arquivo fornece orientações ao Claude Code (claude.ai/code) para trabalhar neste repositório.

## Visão Geral

Pipeline ELT de analytics para e-commerce usando Python (extração + carga) e dbt (transformação). Implementa a Arquitetura Medallion (Bronze → Silver → Gold) com três data marts de domínio na camada Gold. Stack gerenciada via uv workspace; pipeline containerizado via Docker.

## Estrutura

- `extract_load/` — pacote Python: etapas Extract + Load (S3 → Postgres schema `public`)
- `transform/` — projeto dbt: etapa Transform (Bronze → Silver → Gold)
- `pyproject.toml` (raiz) — workspace uv + ruff + pytest
- `docker-compose.yml` — orquestra os 2 serviços (extract, dbt)
- `.env` (gitignored) — segredos consumidos pelos dois pacotes
- `.env.example` — template versionado

## Comandos Principais

### Setup inicial

```bash
rm -rf .venv                       # apaga venv antiga (se existir, criada com pip)
uv sync --all-packages             # instala workspace inteiro em .venv/ na raiz
cp .env.example .env               # criar .env e preencher com credenciais reais
```

### Extract + Load (Python)

```bash
uv run --package extract_load python -m extract_load
```

Lê 4 Parquets do bucket S3 (Supabase Storage), grava no schema `public` do PostgreSQL.

### Transform (dbt)

```bash
uv run --package transform dbt debug --project-dir transform --profiles-dir transform
uv run --package transform dbt parse --project-dir transform --profiles-dir transform
uv run --package transform dbt run --project-dir transform --profiles-dir transform
uv run --package transform dbt test --project-dir transform --profiles-dir transform
uv run --package transform dbt docs generate --project-dir transform --profiles-dir transform

# Execuções seletivas
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s tag:gold
uv run --package transform dbt run --project-dir transform --profiles-dir transform -m vendas_temporais
uv run --package transform dbt run --project-dir transform --profiles-dir transform --full-refresh
```

**Atalho:** exportar `DBT_PROJECT_DIR=transform` e `DBT_PROFILES_DIR=transform` no shell para omitir as flags.

### Lint e testes

```bash
uv run pytest                    # testes Python (extract_load)
uv run ruff check                # lint
uv run ruff check --fix          # auto-correções
uv run ruff format               # formatter
```

### Docker

```bash
docker compose build
docker compose run --rm extract                # roda EL
docker compose run --rm dbt debug              # qualquer subcomando dbt
docker compose run --rm dbt run
docker compose run --rm dbt test
```

## Arquitetura

**Fluxo de dados:** S3 (Parquet) → módulo Python `extract_load` → schema raw PostgreSQL → transformações dbt

```
S3 Bucket: projeto-ecommerce-analytics
  [vendas, clientes, produtos, preco_competidores].parquet
         ↓ extract_load (boto3 + pandas + SQLAlchemy)
PostgreSQL schema: public (tabelas raw)
         ↓ camada bronze dbt (VIEWs — passagem direta, sem transformação)
PostgreSQL schema: bronze
         ↓ camada silver dbt (TABLEs — limpeza, enriquecimento, cálculos)
PostgreSQL schema: silver
         ↓ camada gold dbt (TABLEs — KPIs por domínio, prontos para dashboards)
  public_gold_sales.vendas_temporais          → Analytics de vendas
  public_gold_cs.clientes_segmentacao         → Segmentação de clientes
  public_gold_pricing.precos_competitividade  → Inteligência de preços
```

**Decisão de materialização:**
- Bronze: VIEWs — sempre reflete os dados raw, armazenamento mínimo
- Silver: TABLEs — persiste dados limpos/enriquecidos como base para o Gold
- Gold: TABLEs — otimizado para performance de consulta, pronto para dashboards

## Estrutura do Projeto dbt

- `transform/dbt_project.yml` — configuração do projeto, materializações, schemas, variáveis (`segmentacao_vip_threshold: 10000`, `segmentacao_top_tier_threshold: 5000`). Profile name: `ecommerce`.
- `transform/profiles.yml` — versionado, lê todas as credenciais via `env_var()`.
- `transform/models/_sources.yml` — mapeia `source('raw', ...)` para o schema `public` do PostgreSQL
- `transform/models/bronze/` — 4 modelos, um por tabela raw
- `transform/models/silver/` — 4 modelos; `silver_vendas.sql` é o mais complexo (dimensões temporais, `receita_total = quantidade × preco_unitario`, classificação de faixa de preço)
- `transform/models/gold/sales/`, `gold/customer_success/`, `gold/pricing/` — 3 modelos de data mart por domínio

## Estrutura do pacote `extract_load/`

- `extract_load/src/extract_load/config.py` — `Settings(BaseSettings)` lê `.env` via pydantic-settings; `SecretStr` para credenciais.
- `extract_load/src/extract_load/extract.py` — `extract(settings)` → `dict[str, DataFrame]`. Levanta `ExtractError`.
- `extract_load/src/extract_load/load.py` — `load(dfs, settings)`. Usa SQLAlchemy + `to_sql(if_exists="replace")`. Levanta `LoadError`.
- `extract_load/src/extract_load/__main__.py` — orquestra `Settings()` → `setup_logging()` → `extract()` → `load()`. Exit code 0/1.
- `extract_load/tests/` — pytest com mocks (boto3, SQLite in-memory).

## Convenções

**Referências de source dbt:** `{{ source('raw', 'nome_tabela') }}` para tabelas raw; `{{ ref('nome_modelo') }}` para rastreamento de linhagem entre modelos dbt.

**Thresholds configuráveis:** Usar `{{ var('segmentacao_vip_threshold', 10000) }}` — não hardcodar valores de regras de negócio.

**Nomenclatura:**
- Modelos dbt: `camada_dominio` (ex: `silver_vendas`, `gold_pricing`)
- Colunas: snake_case em português (`receita_total`, `ticket_medio`, `segmento_cliente`)
- Dimensões temporais: sempre extrair `ano`, `mes`, `dia`, `dia_semana`, `hora` na camada silver para uso downstream

**Tratamento de nulos:** Usar `COALESCE(valor, 0)` para colunas numéricas que podem estar ausentes (especialmente nas tabelas de preços).

## Configuração de Ambiente

**Não versionado no git:**
- `.env` — credenciais reais (PostgreSQL + Supabase Storage S3). Criar a partir de `.env.example`.

**Versionado, sem segredos:**
- `.env.example` — template com placeholders.
- `transform/profiles.yml` — profile dbt lendo via `env_var()`.

**Variáveis no `.env` (todas obrigatórias salvo as com default):**
- `POSTGRES_HOST`, `POSTGRES_PORT` (default 5432), `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_SCHEMA` (default `public`), `POSTGRES_SSLMODE` (default `require`)
- `S3_ENDPOINT_URL`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET`
- `LOG_LEVEL` (default `INFO`)

`POSTGRES_USER` no Supabase pooler tem formato `postgres.<PROJECT_REF>`. Usar **session pooler (porta 5432)** — não usar transaction pooler (6543) com dbt.

## Dashboard (case-01)

Dashboard Streamlit para 3 diretores do e-commerce, conectando ao PostgreSQL (Supabase) e consumindo os 3 data marts gold.

**Stack:** Python 3.10+, Streamlit, Plotly, psycopg2-binary, python-dotenv

**Banco de dados:** connection string via variável de ambiente `POSTGRES_URL` no `.env`. Ver `.llm/database.md` para schemas completos das tabelas gold.

**Regras:**
- Formatar valores monetários em reais (R$)
- Usar Plotly para todos os gráficos (não matplotlib)
- Layout wide no Streamlit

## Agente de Relatórios Diários (case-02)

Script Python que consulta os 3 data marts gold no PostgreSQL, envia os dados para a API do Claude e gera um relatório executivo diário para 3 diretores (Comercial, CS, Pricing).

**Stack:** Python 3.10+, anthropic (SDK), psycopg2-binary, pandas, python-dotenv

**Banco de dados:** connection string via `POSTGRES_URL` no `.env`. Ver `.llm/database.md` para schemas completos.

**API:** chave da Anthropic via `ANTHROPIC_API_KEY` no `.env`. Usar modelo `claude-sonnet-4-20250514` para custo reduzido.

**Regras:**
- Tratar erros de conexão antes de chamar a API
- Salvar relatório como `.md` com data no nome do arquivo
- Logging com timestamps em cada etapa

## Extensões Planejadas (ver `.llm/`)

- **case-01-dashboard:** Dashboard Streamlit com 3 páginas (Vendas, Customer Success, Pricing)
- **case-02-agente:** Agente Python com API Claude para relatórios executivos diários
