# Transform (dbt)

## Comandos

```bash
# Atalho: export DBT_PROJECT_DIR=transform DBT_PROFILES_DIR=transform

uv run --package transform dbt run    --project-dir transform --profiles-dir transform
uv run --package transform dbt test   --project-dir transform --profiles-dir transform
uv run --package transform dbt parse  --project-dir transform --profiles-dir transform
uv run --package transform dbt debug  --project-dir transform --profiles-dir transform
uv run --package transform dbt docs generate --project-dir transform --profiles-dir transform

# Runs seletivos
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s tag:gold
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s gold_sales_vendas_temporais
uv run --package transform dbt run --project-dir transform --profiles-dir transform --full-refresh

# Via Docker
docker compose run --rm dbt run
docker compose run --rm dbt test
docker compose run --rm dbt debug
```

## Arquivos Chave

- `dbt_project.yml` — materializações, schemas, variáveis (`segmentacao_vip_threshold: 10000`, `segmentacao_top_tier_threshold: 5000`); profile name: `ecommerce`
- `profiles.yml` — versionado, lê credenciais via `env_var()`
- `models/_sources.yml` — mapeia `source('raw', ...)` → schema `public`

## Convenções

- Use `{{ source('raw', 'tabela') }}` para fontes raw; `{{ ref('modelo') }}` entre modelos
- Thresholds via `{{ var('segmentacao_vip_threshold', 10000) }}` — nunca hardcodar regras de negócio
- Supabase: **session pooler porta 5432** — transaction pooler (6543) não é compatível com dbt
- Silver: filtrar nulos em chaves/datas críticas; atributos descritivos → `'NAO_INFORMADO'`; produtos inferidos → `status_cadastro = 'INFERIDO'`
- Gold: `COALESCE(valor, 0)` apenas em métricas agregadas onde ausência significa zero

## Spec Completa

@PRD-dbt.md
