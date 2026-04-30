# Extract + Load

## Setup Inicial

```bash
rm -rf .venv
uv sync --all-packages
cp .env.example .env  # preencher com credenciais reais
```

## Comandos

```bash
# Produção
uv run --package extract_load python -m extract_load

# Testes
uv run pytest

# Lint e format
uv run ruff check
uv run ruff check --fix
uv run ruff format

# Via Docker
docker compose build
docker compose run --rm extract
```

## Estrutura do Pacote

- `config.py` — `Settings(BaseSettings)`, lê `.env` via pydantic-settings; `SecretStr` para credenciais
- `extract.py` — `extract(settings)` → `dict[str, DataFrame]`; levanta `ExtractError`
- `load.py` — `load(dfs, settings)`, SQLAlchemy + `to_sql(if_exists="replace")`; levanta `LoadError`
- `__main__.py` — orquestra `Settings()` → `setup_logging()` → `extract()` → `load()`; exit code 0/1
- `tests/` — pytest com mocks de boto3 e SQLite in-memory

## Convenções

- Erros de extração levantam `ExtractError`; de carga, `LoadError` — nunca engolir exceções
- Credenciais sempre via `Settings`; nunca hardcodar valores de `.env`
- Lê 4 Parquets do S3 (`vendas`, `clientes`, `produtos`, `preco_competidores`) e grava no schema `public`
