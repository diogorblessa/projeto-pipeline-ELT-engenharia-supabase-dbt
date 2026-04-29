# Reorganização ELT — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganizar o projeto ELT para uma estrutura `extract_load/` + `transform/` com uv workspace, Docker, ruff, pytest, e gestão de segredos centralizada via `.env` único — sem expor credenciais em momento algum.

**Architecture:** uv workspace na raiz com 2 pacotes Python (`extract_load`, `transform`). EL é um módulo Python com config/extract/load/__main__ separados. T continua sendo dbt mas com `profiles.yml` versionado lendo via `env_var()`. Tudo dockerizado em 2 imagens orquestradas por docker-compose. Banco PostgreSQL é remoto (Supabase).

**Tech Stack:** Python 3.11, uv (workspace + lock), pydantic-settings (validação de env), boto3, pandas+pyarrow, SQLAlchemy 2 + psycopg2-binary, dbt-core 1.8 + dbt-postgres, ruff (lint+format), pytest, Docker + docker-compose.

**Spec:** `docs/superpowers/specs/2026-04-28-reorganizacao-elt-design.md`

---

## Pré-requisitos do usuário

- [ ] **Rotacionou as credenciais expostas no Supabase** (S3 access keys + senha do PostgreSQL).
- [ ] Tem `uv` instalado (`uv --version` retorna 0.4+; senão instalar via [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/)).
- [ ] Tem Docker Desktop instalado e rodando (`docker version` retorna 24+).
- [ ] Tem o branch limpo ou consciente das mudanças pendentes (`git status`).

**SE QUALQUER UM DOS DOIS PRIMEIROS NÃO ESTIVER OK, PARAR.** Não prosseguir sem rotação de credenciais — caso contrário, qualquer cópia residual do `data_lake_connect.py` antigo continua sendo um vetor ativo.

---

## File Structure

### Arquivos novos (raiz)

| Path | Responsabilidade |
|---|---|
| `pyproject.toml` | Workspace uv + config ruff + config pytest. Sem build-system (não é pacote instalável). |
| `uv.lock` | Lockfile gerado por `uv sync`. Versionado. |
| `.python-version` | Pin Python 3.11. Versionado. |
| `.env.example` | Template de variáveis com placeholders. Versionado. |
| `.dockerignore` | Bloqueia `.env`, `.venv`, `target/`, `logs/` do build context. |
| `docker-compose.yml` | 2 serviços (extract, dbt). Banco remoto. |
| `README.md` | Quickstart curto. |

### Arquivos novos (extract_load/)

| Path | Responsabilidade |
|---|---|
| `extract_load/pyproject.toml` | Deps do pacote: boto3, pandas, pyarrow, sqlalchemy, psycopg2-binary, pydantic-settings. |
| `extract_load/Dockerfile` | Multi-stage build com uv. |
| `extract_load/src/extract_load/__init__.py` | Marca o pacote, expõe `__version__`. |
| `extract_load/src/extract_load/__main__.py` | Entrypoint: carrega Settings, configura logging, orquestra extract→load. |
| `extract_load/src/extract_load/config.py` | `Settings(BaseSettings)` + constante `TABELAS`. |
| `extract_load/src/extract_load/extract.py` | `extract(settings) -> dict[str, DataFrame]`. Define `ExtractError`. |
| `extract_load/src/extract_load/load.py` | `load(dfs, settings) -> None`. Define `LoadError`. |
| `extract_load/tests/test_config.py` | Validação de env, SecretStr não vaza. |
| `extract_load/tests/test_extract.py` | boto3 mockado, retorna DataFrames. |
| `extract_load/tests/test_load.py` | SQLAlchemy SQLite in-memory. |

### Arquivos novos (transform/)

| Path | Responsabilidade |
|---|---|
| `transform/pyproject.toml` | Deps: dbt-core>=1.8,<1.10, dbt-postgres>=1.8,<1.10. |
| `transform/Dockerfile` | Multi-stage build com uv. |
| `transform/profiles.yml` | Profile dbt versionado, lê via `env_var()`. |

### Arquivos modificados

| Path | Mudança |
|---|---|
| `.gitignore` | Remove linha `profiles.yml` (versionamos `transform/profiles.yml`). |
| `CLAUDE.md` | Atualiza paths/comandos/profile dbt. |

### Renomes

| De | Para |
|---|---|
| `ecommerce/` | `transform/` (via `git mv`) |

### Deletes

| Path | Motivo |
|---|---|
| `extract_python/data_lake_connect.py` | Contém credenciais hardcoded. Substituído por módulos novos. Untracked, sem perda de histórico. |
| `extract_python/` | Pasta substituída por `extract_load/`. |
| `.venv/` | Recriada por `uv sync` (foi feita com pip+venv, incompatível com workspace). |

---

## Tasks

### Task 1: Pré-flight

**Description:** Validar pré-requisitos antes de qualquer mudança no filesystem.

- [ ] **Step 1: Confirmar rotação de credenciais (BLOQUEANTE)**

Pergunte explicitamente ao usuário: "Você já rotacionou as S3 access keys e a senha do PostgreSQL no Supabase?" Se a resposta não for um "sim" claro, **parar a execução**. Caso contrário, prosseguir.

- [ ] **Step 2: Verificar `uv` instalado**

```bash
uv --version
```
Expected: algo como `uv 0.4.x` ou superior. Se "command not found", parar e instruir o usuário a instalar.

- [ ] **Step 3: Verificar Docker disponível**

```bash
docker version --format '{{.Server.Version}}'
```
Expected: número de versão (ex: `27.3.1`). Se erro de conexão, instruir a abrir o Docker Desktop.

- [ ] **Step 4: Snapshot do git status**

```bash
git status --short
```
Expected output (estado conhecido):
```
 D ecommerce/PRD-ecommerce-dbt.md
?? .llm/
?? CLAUDE.md
?? docs/
?? ecommerce/PRD-dbt.md
?? extract_python/
```

Se houver outros arquivos modificados não esperados, pausar e revisar com o usuário antes de continuar.

---

### Task 2: Limpeza inicial (delete `.venv/` e `extract_python/`)

**Files:**
- Delete: `.venv/`
- Delete: `extract_python/data_lake_connect.py`
- Delete: `extract_python/`

**Description:** Apagar a venv antiga (incompatível com uv workspace) e a pasta `extract_python/` que contém credenciais hardcoded.

- [ ] **Step 1: Apagar `.venv/`**

```bash
rm -rf .venv
ls -la .venv 2>&1 | head -1
```
Expected: `ls: cannot access '.venv': No such file or directory`

- [ ] **Step 2: Apagar `extract_python/`**

```bash
rm -rf extract_python
ls -la extract_python 2>&1 | head -1
```
Expected: `ls: cannot access 'extract_python': No such file or directory`

- [ ] **Step 3: Confirmar que git status reflete a remoção do `extract_python/` untracked**

```bash
git status --short | grep -E "extract_python" || echo "extract_python removed from status"
```
Expected: `extract_python removed from status`

(Sem commit ainda — `.venv/` é gitignored, `extract_python/` era untracked.)

---

### Task 3: Renomear `ecommerce/` → `transform/`

**Files:**
- Rename: `ecommerce/` → `transform/`

**Description:** Mover a pasta dbt para o nome novo, preservando histórico via `git mv`.

- [ ] **Step 1: Limpar artefatos dbt antes do rename**

Pastas geradas (`target/`, `logs/`, `dbt_packages/`) são gitignored mas existem fisicamente. Não atrapalham `git mv`, mas vamos limpar para reduzir lixo:

```bash
rm -rf ecommerce/target ecommerce/logs ecommerce/dbt_packages
```
Expected: silêncio.

- [ ] **Step 2: Executar `git mv`**

```bash
git mv ecommerce transform
```
Expected: silêncio (sucesso).

- [ ] **Step 3: Verificar status**

```bash
git status --short | head -20
```
Expected (resumido): vários `R  ecommerce/... -> transform/...` para arquivos rastreados; `?? transform/PRD-dbt.md` (untracked herdado).

- [ ] **Step 4: Stagear o `transform/PRD-dbt.md` (era untracked em `ecommerce/`)**

```bash
git add transform/PRD-dbt.md
```
Expected: silêncio.

- [ ] **Step 5: Stagear a remoção do PRD-ecommerce-dbt.md (estava como deleted)**

```bash
git add -u transform/
git status --short | head -20
```
Expected: agora todos os arquivos do antigo `ecommerce/` aparecem com `R  ...` (rename) ou `A  transform/PRD-dbt.md`.

- [ ] **Step 6: Commit do rename**

```bash
git commit -m "refactor: rename ecommerce/ to transform/ to reflect ELT layer

A pasta passa a refletir explicitamente a etapa T do pipeline.
Conteúdo dos modelos dbt permanece intocado."
```
Expected: commit criado, hash mostrado.

---

### Task 4: Atualizar `.gitignore`

**Files:**
- Modify: `.gitignore`

**Description:** Remover a regra global `profiles.yml` (passamos a versionar `transform/profiles.yml`).

- [ ] **Step 1: Editar `.gitignore`**

Substituir a linha 27 (`profiles.yml`) por um comentário explicativo. Conteúdo final do `.gitignore`:

```
# Python
.venv/
venv/
env/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Environment / secrets
.env
.env.*
!.env.example
*.pem
*.key

# dbt
target/
dbt_packages/
logs/
.user.yml
# profiles.yml NÃO é ignorado — versionamos transform/profiles.yml
# (sem segredos, lê tudo via env_var())

# Claude / IDE
.claude/
.vscode/
.idea/
*.swp
docs/

# OS
.DS_Store
Thumbs.db
desktop.ini
```

- [ ] **Step 2: Confirmar diff**

```bash
git diff .gitignore
```
Expected: linha `profiles.yml` removida; comentário explicativo adicionado.

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: allow versioning transform/profiles.yml

Remove regra global \`profiles.yml\` do .gitignore. O arquivo
transform/profiles.yml é versionado mas não contém segredos —
lê tudo via env_var()."
```
Expected: commit criado.

---

### Task 5: Criar arquivos de configuração da raiz

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `.env.example`
- Create: `.dockerignore`

**Description:** Criar os 4 arquivos que definem o workspace, pin de Python, template de segredos e bloqueio do Docker build context.

- [ ] **Step 1: Criar `pyproject.toml` da raiz**

```toml
[project]
name = "projeto-pipeline-elt"
version = "0.1.0"
description = "Pipeline ELT: S3 -> PostgreSQL -> dbt (Bronze/Silver/Gold)"
requires-python = ">=3.11"

[tool.uv.workspace]
members = ["extract_load", "transform"]

[dependency-groups]
dev = [
    "ruff>=0.6",
    "pytest>=8.0",
]

# ---- ruff ----
[tool.ruff]
target-version = "py311"
line-length = 100
extend-exclude = ["transform/target", "transform/dbt_packages", "transform/logs"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "S", "SIM", "RUF"]

[tool.ruff.lint.per-file-ignores]
"**/tests/**" = ["S101"]

# ---- pytest ----
[tool.pytest.ini_options]
testpaths = ["extract_load/tests"]
addopts = "-ra --strict-markers"
```

- [ ] **Step 2: Criar `.python-version`**

```
3.11
```

- [ ] **Step 3: Criar `.env.example`**

```bash
# ============================================================
# Pipeline ELT — variaveis de ambiente
# ------------------------------------------------------------
# 1. Copie este arquivo: cp .env.example .env
# 2. Preencha com seus valores reais (NUNCA commite o .env)
# 3. Variaveis sem default sao OBRIGATORIAS
# ============================================================

# ----- PostgreSQL (Supabase) -----
# Host: Supabase Project Settings -> Database -> Connection pooler
#       Use "Session" pooler (porta 5432). NAO use Transaction (6543) com dbt.
POSTGRES_HOST=aws-1-REGION.pooler.supabase.com
POSTGRES_PORT=5432
POSTGRES_DB=postgres

# Formato no Supabase: postgres.<PROJECT_REF>
# Ex: postgres.abc123xyz456
POSTGRES_USER=postgres.YOUR_PROJECT_REF
POSTGRES_PASSWORD=CHANGE_ME

# Schema onde o EL grava as tabelas raw (default: public)
POSTGRES_SCHEMA=public

# TLS - Supabase exige (default: require)
POSTGRES_SSLMODE=require

# ----- Supabase Storage (S3-compatible) -----
# Endpoint: Supabase Project Settings -> Storage -> S3 Connection
S3_ENDPOINT_URL=https://YOUR_PROJECT_REF.storage.supabase.co/storage/v1/s3
S3_REGION=us-east-2

# Geradas em: Storage -> S3 Access Keys
S3_ACCESS_KEY_ID=CHANGE_ME
S3_SECRET_ACCESS_KEY=CHANGE_ME

# Nome do bucket onde estao os 4 arquivos .parquet
S3_BUCKET=projeto-ecommerce-analytics

# ----- Logging -----
# Niveis: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO
```

- [ ] **Step 4: Criar `.dockerignore`**

```
# Git
.git
.gitignore

# Python
.venv
__pycache__
*.pyc
.pytest_cache
.ruff_cache
.mypy_cache

# Secrets
.env
.env.*
!.env.example

# dbt
transform/target
transform/logs
transform/dbt_packages

# Docs / IDE / OS
.vscode
.idea
.claude
.llm
docs
*.md
!README.md
.DS_Store
Thumbs.db
```

- [ ] **Step 5: Confirmar criação dos 4 arquivos**

```bash
ls -la pyproject.toml .python-version .env.example .dockerignore
```
Expected: as 4 entradas listadas com tamanhos não-zero.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .python-version .env.example .dockerignore
git commit -m "chore: add root workspace config (pyproject, .python-version, .env.example, .dockerignore)

Configura uv workspace, ruff, pytest e template de segredos.
.env real continua gitignored."
```
Expected: commit criado.

---

### Task 6: Estrutura dos pacotes + uv sync

**Files:**
- Create: `extract_load/pyproject.toml`
- Create: `extract_load/src/extract_load/__init__.py`
- Create: `transform/pyproject.toml`
- Create: `uv.lock` (gerado)

**Description:** Criar `pyproject.toml` dos dois pacotes do workspace e o esqueleto mínimo do `extract_load` para que `uv sync` funcione e gere `uv.lock`.

- [ ] **Step 1: Criar `extract_load/pyproject.toml`**

```toml
[project]
name = "extract_load"
version = "0.1.0"
description = "Pipeline EL: S3 -> PostgreSQL raw"
requires-python = ">=3.11"
dependencies = [
    "boto3>=1.34",
    "pandas>=2.2",
    "pyarrow>=15.0",
    "sqlalchemy>=2.0",
    "psycopg2-binary>=2.9",
    "pydantic-settings>=2.4",
]

[build-system]
requires = ["hatchling>=1.0"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/extract_load"]
```

- [ ] **Step 2: Criar `extract_load/src/extract_load/__init__.py`**

```python
"""Pipeline ELT — etapas Extract + Load (S3 -> PostgreSQL raw)."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Criar `transform/pyproject.toml`**

```toml
[project]
name = "transform"
version = "0.1.0"
description = "Pipeline T: dbt transformations (Bronze/Silver/Gold)"
requires-python = ">=3.11"
dependencies = [
    "dbt-core>=1.8,<1.10",
    "dbt-postgres>=1.8,<1.10",
]

[build-system]
requires = ["hatchling>=1.0"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
bypass-selection = true
```

- [ ] **Step 4: Rodar `uv sync` (gera `.venv/` e `uv.lock`)**

```bash
uv sync
```
Expected: uv resolve o workspace, baixa deps, cria `.venv/` na raiz e `uv.lock`. Pode demorar 1-3 min na primeira vez. Saída termina com algo como `Installed N packages in Xs`.

- [ ] **Step 5: Validar imports básicos**

```bash
uv run python -c "import extract_load; import boto3; import dbt.cli.main; print('imports OK')"
```
Expected: `imports OK`. Se falhar, revisar pyproject.tomls.

- [ ] **Step 6: Commit**

```bash
git add extract_load/pyproject.toml extract_load/src/extract_load/__init__.py transform/pyproject.toml uv.lock
git commit -m "chore: scaffold uv workspace with extract_load and transform packages

Cria pyproject.toml dos 2 pacotes do workspace, esqueleto do
extract_load e gera uv.lock unificado."
```
Expected: commit criado.

---

### Task 7: TDD — `config.py`

**Files:**
- Create: `extract_load/tests/test_config.py`
- Create: `extract_load/src/extract_load/config.py`

**Description:** Implementar `Settings` (pydantic-settings) com SecretStr para credenciais. Testes garantem: env válido instancia OK, env incompleto falha, SecretStr não vaza em repr.

- [ ] **Step 1: Escrever os testes (failing)**

```python
# extract_load/tests/test_config.py
import pytest
from pydantic import ValidationError


VALID_ENV = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_DB": "test",
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "pwd_secret_value",
    "S3_ENDPOINT_URL": "https://example.com",
    "S3_REGION": "us-east-1",
    "S3_ACCESS_KEY_ID": "key_secret_value",
    "S3_SECRET_ACCESS_KEY": "ssk_secret_value",
    "S3_BUCKET": "bucket",
}


@pytest.fixture
def clean_env(monkeypatch):
    """Garante env limpo, sem ler .env do projeto."""
    for k in list(VALID_ENV.keys()) + ["POSTGRES_PORT", "POSTGRES_SCHEMA",
                                        "POSTGRES_SSLMODE", "LOG_LEVEL"]:
        monkeypatch.delenv(k, raising=False)


def test_settings_loads_from_env(monkeypatch, clean_env):
    from extract_load.config import Settings

    for k, v in VALID_ENV.items():
        monkeypatch.setenv(k, v)
    settings = Settings(_env_file=None)

    assert settings.postgres_host == "localhost"
    assert settings.postgres_db == "test"
    assert settings.postgres_user == "user"
    assert settings.postgres_password.get_secret_value() == "pwd_secret_value"
    assert settings.postgres_port == 5432  # default
    assert settings.postgres_schema == "public"  # default
    assert settings.postgres_sslmode == "require"  # default
    assert settings.s3_bucket == "bucket"
    assert settings.log_level == "INFO"  # default


def test_settings_missing_required_var_raises(monkeypatch, clean_env):
    from extract_load.config import Settings

    minimal = {k: v for k, v in VALID_ENV.items() if k != "POSTGRES_PASSWORD"}
    for k, v in minimal.items():
        monkeypatch.setenv(k, v)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_secrets_not_in_repr(monkeypatch, clean_env):
    from extract_load.config import Settings

    for k, v in VALID_ENV.items():
        monkeypatch.setenv(k, v)
    settings = Settings(_env_file=None)
    rendered = repr(settings)

    assert "pwd_secret_value" not in rendered
    assert "key_secret_value" not in rendered
    assert "ssk_secret_value" not in rendered


def test_tabelas_constant_is_correct():
    from extract_load.config import TABELAS

    assert TABELAS == ("vendas", "clientes", "produtos", "preco_competidores")
```

- [ ] **Step 2: Rodar testes — devem falhar com ImportError**

```bash
uv run pytest extract_load/tests/test_config.py -v
```
Expected: erros tipo `ModuleNotFoundError: No module named 'extract_load.config'` ou similar (4 testes falhando).

- [ ] **Step 3: Implementar `config.py`**

```python
# extract_load/src/extract_load/config.py
from typing import Final

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

TABELAS: Final[tuple[str, ...]] = ("vendas", "clientes", "produtos", "preco_competidores")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # PostgreSQL
    postgres_host: str
    postgres_port: int = 5432
    postgres_db: str
    postgres_user: str
    postgres_password: SecretStr
    postgres_schema: str = "public"
    postgres_sslmode: str = "require"

    # S3 / Supabase Storage
    s3_endpoint_url: str
    s3_region: str
    s3_access_key_id: SecretStr
    s3_secret_access_key: SecretStr
    s3_bucket: str

    # Logging
    log_level: str = "INFO"
```

- [ ] **Step 4: Rodar testes — devem passar**

```bash
uv run pytest extract_load/tests/test_config.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add extract_load/src/extract_load/config.py extract_load/tests/test_config.py
git commit -m "feat(extract_load): add Settings with pydantic-settings and SecretStr

Define TABELAS constant. Settings carrega do .env com SecretStr
para credenciais (S3 + Postgres). Testes cobrem env valido,
env incompleto e protecao contra leak via repr."
```
Expected: commit criado.

---

### Task 8: TDD — `extract.py`

**Files:**
- Create: `extract_load/tests/test_extract.py`
- Create: `extract_load/src/extract_load/extract.py`

**Description:** `extract(settings)` baixa 4 Parquets do S3 e devolve `dict[str, DataFrame]`. boto3 mockado nos testes.

- [ ] **Step 1: Escrever os testes (failing)**

```python
# extract_load/tests/test_extract.py
from io import BytesIO
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


VALID_ENV = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_DB": "test",
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "pwd",
    "S3_ENDPOINT_URL": "https://example.com",
    "S3_REGION": "us-east-1",
    "S3_ACCESS_KEY_ID": "key",
    "S3_SECRET_ACCESS_KEY": "secret",
    "S3_BUCKET": "test-bucket",
}


def _parquet_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    df.to_parquet(buf, engine="pyarrow")
    return buf.getvalue()


def _make_settings(monkeypatch):
    from extract_load.config import Settings

    for k in list(VALID_ENV.keys()) + ["POSTGRES_PORT", "POSTGRES_SCHEMA",
                                        "POSTGRES_SSLMODE", "LOG_LEVEL"]:
        monkeypatch.delenv(k, raising=False)
    for k, v in VALID_ENV.items():
        monkeypatch.setenv(k, v)
    return Settings(_env_file=None)


@patch("extract_load.extract.boto3.client")
def test_extract_returns_four_dataframes(mock_boto, monkeypatch):
    from extract_load.extract import extract

    sample_df = pd.DataFrame({"id": [1, 2, 3]})
    payload = _parquet_bytes(sample_df)

    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: payload)}
    mock_boto.return_value = mock_s3

    settings = _make_settings(monkeypatch)
    result = extract(settings)

    assert set(result.keys()) == {"vendas", "clientes", "produtos", "preco_competidores"}
    for df in result.values():
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3


@patch("extract_load.extract.boto3.client")
def test_extract_passes_credentials_to_boto3(mock_boto, monkeypatch):
    from extract_load.extract import extract

    sample_df = pd.DataFrame({"id": [1]})
    payload = _parquet_bytes(sample_df)
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: payload)}
    mock_boto.return_value = mock_s3

    settings = _make_settings(monkeypatch)
    extract(settings)

    args, kwargs = mock_boto.call_args
    assert args == ("s3",)
    assert kwargs["region_name"] == "us-east-1"
    assert kwargs["endpoint_url"] == "https://example.com"
    assert kwargs["aws_access_key_id"] == "key"
    assert kwargs["aws_secret_access_key"] == "secret"


@patch("extract_load.extract.boto3.client")
def test_extract_raises_extract_error_on_s3_failure(mock_boto, monkeypatch):
    from botocore.exceptions import ClientError

    from extract_load.extract import ExtractError, extract

    mock_s3 = MagicMock()
    mock_s3.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "not found"}}, "GetObject"
    )
    mock_boto.return_value = mock_s3

    settings = _make_settings(monkeypatch)
    with pytest.raises(ExtractError) as exc_info:
        extract(settings)
    assert "vendas" in str(exc_info.value)  # contexto: qual tabela falhou
```

- [ ] **Step 2: Rodar testes — devem falhar (ImportError)**

```bash
uv run pytest extract_load/tests/test_extract.py -v
```
Expected: 3 testes falhando com `ModuleNotFoundError: No module named 'extract_load.extract'`.

- [ ] **Step 3: Implementar `extract.py`**

```python
# extract_load/src/extract_load/extract.py
import io
import logging

import boto3
import pandas as pd
from botocore.exceptions import BotoCoreError, ClientError

from extract_load.config import TABELAS, Settings

log = logging.getLogger(__name__)


class ExtractError(Exception):
    """Raised when extraction from S3 fails."""


def _build_s3_client(settings: Settings):
    return boto3.client(
        "s3",
        region_name=settings.s3_region,
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id.get_secret_value(),
        aws_secret_access_key=settings.s3_secret_access_key.get_secret_value(),
    )


def extract(settings: Settings) -> dict[str, pd.DataFrame]:
    """Download 4 Parquet files from S3 and return as DataFrames keyed by table name."""
    s3 = _build_s3_client(settings)
    dfs: dict[str, pd.DataFrame] = {}

    for tabela in TABELAS:
        key = f"{tabela}.parquet"
        try:
            response = s3.get_object(Bucket=settings.s3_bucket, Key=key)
            payload = response["Body"].read()
            df = pd.read_parquet(io.BytesIO(payload))
        except (BotoCoreError, ClientError) as e:
            raise ExtractError(f"failed to extract {tabela}: {e}") from e

        dfs[tabela] = df
        log.info("extracted: %s (%d rows)", tabela, len(df))

    return dfs
```

- [ ] **Step 4: Rodar testes — devem passar**

```bash
uv run pytest extract_load/tests/test_extract.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add extract_load/src/extract_load/extract.py extract_load/tests/test_extract.py
git commit -m "feat(extract_load): add S3 extraction module

extract() devolve dict[str, DataFrame] das 4 tabelas raw.
Credenciais lidas via SecretStr.get_secret_value() apenas no
ponto de uso (boto3.client). ExtractError encapsula falhas
de S3 com contexto da tabela."
```
Expected: commit criado.

---

### Task 9: TDD — `load.py`

**Files:**
- Create: `extract_load/tests/test_load.py`
- Create: `extract_load/src/extract_load/load.py`

**Description:** `load(dfs, settings)` grava DataFrames como tabelas Postgres usando SQLAlchemy. Testes usam SQLite in-memory (schema="main").

- [ ] **Step 1: Escrever os testes (failing)**

```python
# extract_load/tests/test_load.py
import pandas as pd
import pytest
from sqlalchemy import create_engine, text


VALID_ENV_BASE = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_DB": "test",
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "pwd",
    "POSTGRES_SCHEMA": "main",  # SQLite usa "main" como schema padrao
    "S3_ENDPOINT_URL": "https://example.com",
    "S3_REGION": "us-east-1",
    "S3_ACCESS_KEY_ID": "key",
    "S3_SECRET_ACCESS_KEY": "secret",
    "S3_BUCKET": "test-bucket",
}


@pytest.fixture
def in_memory_engine_factory(monkeypatch):
    """Substitui sqlalchemy.create_engine de load.py por SQLite in-memory partilhada."""
    engine = create_engine("sqlite:///:memory:")

    def fake_create_engine(*args, **kwargs):
        return engine

    monkeypatch.setattr("extract_load.load.create_engine", fake_create_engine)
    return engine


def _make_settings(monkeypatch, **overrides):
    from extract_load.config import Settings

    env = {**VALID_ENV_BASE, **overrides}
    for k in list(VALID_ENV_BASE.keys()) + ["POSTGRES_PORT", "POSTGRES_SSLMODE", "LOG_LEVEL"]:
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return Settings(_env_file=None)


def test_load_inserts_dataframes(in_memory_engine_factory, monkeypatch):
    from extract_load.load import load

    dfs = {
        "vendas": pd.DataFrame({"id_venda": [1, 2, 3], "valor": [10.0, 20.0, 30.0]}),
        "clientes": pd.DataFrame({"id_cliente": [1, 2], "nome": ["a", "b"]}),
    }
    settings = _make_settings(monkeypatch)
    load(dfs, settings)

    with in_memory_engine_factory.connect() as conn:
        n_vendas = conn.execute(text("SELECT COUNT(*) FROM main.vendas")).scalar()
        n_clientes = conn.execute(text("SELECT COUNT(*) FROM main.clientes")).scalar()
    assert n_vendas == 3
    assert n_clientes == 2


def test_load_replaces_existing_table(in_memory_engine_factory, monkeypatch):
    from extract_load.load import load

    settings = _make_settings(monkeypatch)
    load({"vendas": pd.DataFrame({"x": [1, 2, 3, 4, 5]})}, settings)
    load({"vendas": pd.DataFrame({"x": [1]})}, settings)

    with in_memory_engine_factory.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM main.vendas")).scalar()
    assert n == 1


def test_load_raises_load_error_on_failure(monkeypatch):
    from extract_load.load import LoadError, load

    # Engine que sempre falha
    bad_engine = create_engine("sqlite:///:memory:")
    bad_engine.dispose()  # força conexões a falharem

    def fake_create_engine(*args, **kwargs):
        return bad_engine

    monkeypatch.setattr("extract_load.load.create_engine", fake_create_engine)

    # DataFrame com tipos incompativeis com SQLite causa falha em to_sql
    # Caminho mais robusto: mockar to_sql diretamente via DataFrame
    dfs = {"vendas": pd.DataFrame({"x": [1]})}
    settings = _make_settings(monkeypatch)

    # Mock pd.DataFrame.to_sql para levantar
    from sqlalchemy.exc import SQLAlchemyError

    original_to_sql = pd.DataFrame.to_sql

    def fake_to_sql(self, *args, **kwargs):
        raise SQLAlchemyError("simulated failure")

    monkeypatch.setattr(pd.DataFrame, "to_sql", fake_to_sql)
    try:
        with pytest.raises(LoadError) as exc_info:
            load(dfs, settings)
        assert "vendas" in str(exc_info.value)
    finally:
        monkeypatch.setattr(pd.DataFrame, "to_sql", original_to_sql)
```

- [ ] **Step 2: Rodar testes — devem falhar (ImportError)**

```bash
uv run pytest extract_load/tests/test_load.py -v
```
Expected: 3 testes falhando com `ModuleNotFoundError: No module named 'extract_load.load'`.

- [ ] **Step 3: Implementar `load.py`**

```python
# extract_load/src/extract_load/load.py
import logging

import pandas as pd
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from extract_load.config import Settings

log = logging.getLogger(__name__)


class LoadError(Exception):
    """Raised when loading to PostgreSQL fails."""


def _build_url(settings: Settings) -> URL:
    return URL.create(
        drivername="postgresql+psycopg2",
        username=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
    )


def load(dfs: dict[str, pd.DataFrame], settings: Settings) -> None:
    """Replace tables in `settings.postgres_schema` with the given DataFrames."""
    url = _build_url(settings)
    connect_args = {"sslmode": settings.postgres_sslmode}
    engine = create_engine(url, connect_args=connect_args)
    try:
        for tabela, df in dfs.items():
            try:
                df.to_sql(
                    tabela,
                    engine,
                    schema=settings.postgres_schema,
                    if_exists="replace",
                    index=False,
                )
            except SQLAlchemyError as e:
                raise LoadError(f"failed to load {tabela}: {e}") from e
            log.info(
                "loaded: %s (%d rows -> %s.%s)",
                tabela,
                len(df),
                settings.postgres_schema,
                tabela,
            )

        # Verificacao final
        with engine.connect() as conn:
            for tabela in dfs:
                qualified = f"{settings.postgres_schema}.{tabela}"
                count = conn.execute(text(f"SELECT COUNT(*) FROM {qualified}")).scalar()
                log.info("verified: %s = %s rows", qualified, count)
    finally:
        engine.dispose()
```

**Nota sobre `connect_args={"sslmode": ...}`:** o psycopg2 aceita `sslmode`. SQLite (no teste) ignora `connect_args` desconhecidos quando usado via SQLAlchemy.

Atenção: o ruff regra `S608` pode reclamar de SQL string com f-string. O `qualified` aqui vem de `settings.postgres_schema` (controlado por env, não input externo) + chave conhecida. Caso reclame, adicionar `# noqa: S608` na linha — ou trocar por `text(":t").bindparams()` se preferir (não é trivial para identifiers).

- [ ] **Step 4: Rodar testes — devem passar**

```bash
uv run pytest extract_load/tests/test_load.py -v
```
Expected: 3 passed. Se houver warning de SQLAlchemy sobre `connect_args` não usado em SQLite, ignorar.

- [ ] **Step 5: Commit**

```bash
git add extract_load/src/extract_load/load.py extract_load/tests/test_load.py
git commit -m "feat(extract_load): add PostgreSQL load module

load() escreve DataFrames no schema configurado via to_sql.
URL construida com URL.create (escape automatico de senha).
sslmode passado via connect_args. engine.dispose() em finally.
LoadError encapsula falhas com contexto da tabela."
```
Expected: commit criado.

---

### Task 10: Implementar `__main__.py` e validar local

**Files:**
- Create: `extract_load/src/extract_load/__main__.py`

**Description:** Orquestrar Settings → setup_logging → extract → load. Validar pytest e ruff.

- [ ] **Step 1: Criar `__main__.py`**

```python
# extract_load/src/extract_load/__main__.py
import logging
import sys

from extract_load.config import Settings
from extract_load.extract import ExtractError, extract
from extract_load.load import LoadError, load


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )


def main() -> int:
    settings = Settings()  # falha cedo se .env incompleto
    setup_logging(settings.log_level)
    log = logging.getLogger("extract_load")
    log.info("pipeline starting")
    try:
        dfs = extract(settings)
        load(dfs, settings)
    except (ExtractError, LoadError) as e:
        log.error("pipeline failed: %s", e)
        return 1
    log.info("pipeline complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Validar entrypoint sem .env (espera ValidationError do pydantic)**

```bash
uv run python -m extract_load 2>&1 | head -5
```
Expected: erro de validação pydantic listando vars obrigatórias faltantes (`POSTGRES_HOST`, etc.). Isso confirma que o entrypoint chega no `Settings()` e falha cedo. **Sem segredos vazados**.

- [ ] **Step 3: Rodar suite de testes completa**

```bash
uv run pytest -v
```
Expected: 10 passed (4 config + 3 extract + 3 load).

- [ ] **Step 4: Rodar ruff (lint)**

```bash
uv run ruff check
```
Expected: `All checks passed!`. Se aparecer alguma violação `S608` em `load.py`, aplicar `# noqa: S608` na linha do `text(f"SELECT COUNT(*) ...")`.

- [ ] **Step 5: Rodar ruff (formatter)**

```bash
uv run ruff format --check
```
Expected: `N file(s) already formatted`. Se houver diferenças, rodar `uv run ruff format` (sem `--check`) e revisar diff antes de commit.

- [ ] **Step 6: Commit**

```bash
git add extract_load/src/extract_load/__main__.py
git commit -m "feat(extract_load): add __main__ entrypoint with logging setup

Orquestra extract -> load. setup_logging respeita LOG_LEVEL.
Settings() falha cedo se .env incompleto."
```
Expected: commit criado.

---

### Task 11: Criar `extract_load/Dockerfile`

**Files:**
- Create: `extract_load/Dockerfile`

**Description:** Dockerfile multi-stage usando a imagem oficial do uv. Imagem final ~250MB, sem cache de build, usuário não-root.

- [ ] **Step 1: Criar `extract_load/Dockerfile`**

```dockerfile
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
```

- [ ] **Step 2: Build local (não roda — só valida que builda)**

```bash
docker build -f extract_load/Dockerfile -t projeto-elt-extract:test .
```
Expected: build conclui em 1-3 min (primeira vez baixa imagens base). Last line: `naming to docker.io/library/projeto-elt-extract:test`.

- [ ] **Step 3: Validar entrypoint dentro da imagem (sem .env, espera ValidationError)**

```bash
docker run --rm projeto-elt-extract:test 2>&1 | head -5
```
Expected: erro de validação pydantic (mesmo comportamento do host). Confirma que a imagem está bem montada.

- [ ] **Step 4: Commit**

```bash
git add extract_load/Dockerfile
git commit -m "feat(extract_load): add multi-stage Dockerfile with uv

Builder com uv sync --frozen --no-dev --package extract_load.
Runtime usa user nao-root. ENTRYPOINT direto no modulo."
```
Expected: commit criado.

---

### Task 12: Criar `transform/profiles.yml`

**Files:**
- Create: `transform/profiles.yml`

**Description:** Profile dbt versionado, todas as credenciais via `env_var()`.

- [ ] **Step 1: Criar `transform/profiles.yml`**

```yaml
ecommerce:
  target: dev
  outputs:
    dev:
      type: postgres
      host: "{{ env_var('POSTGRES_HOST') }}"
      port: "{{ env_var('POSTGRES_PORT', '5432') | as_number }}"
      user: "{{ env_var('POSTGRES_USER') }}"
      password: "{{ env_var('POSTGRES_PASSWORD') }}"
      dbname: "{{ env_var('POSTGRES_DB') }}"
      schema: "{{ env_var('POSTGRES_SCHEMA', 'public') }}"
      threads: 4
      keepalives_idle: 0
      sslmode: "{{ env_var('POSTGRES_SSLMODE', 'require') }}"
```

- [ ] **Step 2: Validar parsing (sem conectar ainda)**

```bash
uv run --package transform dbt parse --project-dir transform --profiles-dir transform 2>&1 | tail -5
```
Expected: `Found N models, ...` ou similar. Se falhar com erro de credencial, é OK por enquanto (parse pode tentar resolver env_var; o usuário ainda não tem `.env` real).

Se aparecer `Env var required but not provided: 'POSTGRES_HOST'`, isso confirma que o profile está lendo via env_var corretamente — pular para o próximo step.

- [ ] **Step 3: Commit**

```bash
git add transform/profiles.yml
git commit -m "feat(transform): version profiles.yml reading via env_var()

Profile dbt versionado sem segredos. Todas credenciais
vem do .env via env_var(). Inclui keepalives_idle=0
recomendado para Supabase pooler."
```
Expected: commit criado.

---

### Task 13: Criar `transform/Dockerfile`

**Files:**
- Create: `transform/Dockerfile`

**Description:** Dockerfile multi-stage para o serviço dbt. ENTRYPOINT permite passar subcomandos.

- [ ] **Step 1: Criar `transform/Dockerfile`**

```dockerfile
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
```

- [ ] **Step 2: Build local**

```bash
docker build -f transform/Dockerfile -t projeto-elt-dbt:test .
```
Expected: build conclui em 1-3 min. Last line com `naming to docker.io/library/projeto-elt-dbt:test`.

- [ ] **Step 3: Validar comando default (--help)**

```bash
docker run --rm projeto-elt-dbt:test
```
Expected: help do dbt impresso.

- [ ] **Step 4: Validar parse sem .env (espera erro de env_var)**

```bash
docker run --rm projeto-elt-dbt:test parse 2>&1 | tail -5
```
Expected: `Env var required but not provided: 'POSTGRES_HOST'` ou similar. Confirma que o profile está sendo lido.

- [ ] **Step 5: Commit**

```bash
git add transform/Dockerfile
git commit -m "feat(transform): add multi-stage Dockerfile with uv

Builder instala dbt-core e dbt-postgres via workspace.
Runtime exporta DBT_PROFILES_DIR e DBT_PROJECT_DIR.
ENTRYPOINT dbt permite passar subcomando."
```
Expected: commit criado.

---

### Task 14: Criar `docker-compose.yml`

**Files:**
- Create: `docker-compose.yml`

**Description:** Orquestrador local. Banco é remoto (Supabase) — sem PostgreSQL no compose.

- [ ] **Step 1: Criar `docker-compose.yml`**

```yaml
services:
  extract:
    build:
      context: .
      dockerfile: extract_load/Dockerfile
    image: projeto-elt-extract:latest
    env_file: .env
    restart: "no"

  dbt:
    build:
      context: .
      dockerfile: transform/Dockerfile
    image: projeto-elt-dbt:latest
    env_file: .env
    restart: "no"
    # OPCIONAL — descomentar para persistir artefatos do dbt entre runs:
    # volumes:
    #   - ./transform/target:/app/transform/target
    #   - ./transform/logs:/app/transform/logs
```

- [ ] **Step 2: Validar config do compose**

```bash
docker compose config --quiet
echo "compose config OK"
```
Expected: silêncio + `compose config OK`. Se aparecer warning sobre `.env` não encontrado, é normal (ainda não foi criado pelo usuário).

- [ ] **Step 3: Build de ambos os serviços**

```bash
docker compose build
```
Expected: ambos os builds (extract, dbt) concluem. Última linha mostra ambas imagens criadas. (Reaproveita layers se Tasks 11/13 já foram executadas.)

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add docker-compose with extract and dbt services

Banco e remoto (Supabase), sem PostgreSQL local.
.env injetado via env_file. Volumes para target/logs
do dbt deixados como opcao comentada."
```
Expected: commit criado.

---

### Task 15: Criar `README.md`

**Files:**
- Create: `README.md`

**Description:** Quickstart com comandos copy-paste.

- [ ] **Step 1: Criar `README.md`**

```markdown
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
uv sync

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
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add quickstart README

Setup local, comandos host, comandos Docker, bloco curto
sobre seguranca. Aponta para CLAUDE.md e .llm/database.md
para detalhes adicionais."
```
Expected: commit criado.

---

### Task 16: Atualizar `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

**Description:** Substituir paths antigos (`ecommerce/`, `extract_python/`) pelos novos. Atualizar comandos para uv. Mencionar `transform/profiles.yml`. Manter intactas as seções de cases 01/02.

- [ ] **Step 1: Sobrescrever `CLAUDE.md` com conteúdo atualizado**

```markdown
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
rm -rf .venv               # apaga venv antiga (se existir, criada com pip)
uv sync                    # instala workspace inteiro em .venv/ na raiz
cp .env.example .env       # criar .env e preencher com credenciais reais
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
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s gold_sales_vendas_temporais
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
  public_gold_sales.gold_sales_vendas_temporais          → Analytics de vendas
  public_gold_cs.gold_customer_success_clientes_segmentacao         → Segmentação de clientes
  public_gold_pricing.gold_pricing_precos_competitividade  → Inteligência de preços
```

**Decisão de materialização:**
- Bronze: VIEWs — sempre reflete os dados raw, armazenamento mínimo
- Silver: TABLEs — persiste dados limpos/enriquecidos como base para o Gold
- Gold: TABLEs — otimizado para performance de consulta, pronto para dashboards

## Estrutura do Projeto dbt

Nota posterior: a camada Gold foi refinada para `gold/dimensional/` e `gold/marts/<setor>/`, mantendo os marts finais com prefixo `gold_*`.
- `transform/dbt_project.yml` — configuração do projeto, materializações, schemas, variáveis (`segmentacao_vip_threshold: 10000`, `segmentacao_top_tier_threshold: 5000`). Profile name: `ecommerce`.
- `transform/profiles.yml` — versionado, lê todas as credenciais via `env_var()`.
- `transform/models/_sources.yml` — mapeia `source('raw', ...)` para o schema `public` do PostgreSQL
- `transform/models/bronze/` — 4 modelos, um por tabela raw
- `transform/models/silver/` — 4 modelos; `silver_vendas.sql` é o mais complexo (dimensões temporais, `receita_total = quantidade × preco_unitario`, classificação de faixa de preço)
- `transform/models/gold/marts/sales/`, `gold/marts/customer_success/`, `gold/marts/pricing/` — 3 modelos de data mart por domínio

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
```

- [ ] **Step 2: Confirmar diff razoável**

```bash
git status --short CLAUDE.md
```
Expected: `?? CLAUDE.md` (untracked) ou ` M CLAUDE.md` (modificado). Em qualquer caso, prosseguir.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md to reflect new ELT structure

Substitui paths antigos (ecommerce/, extract_python/) por
transform/ e extract_load/. Atualiza comandos para uv.
Adiciona secoes Docker, lint/testes. Mantem intactas
secoes case-01 (dashboard) e case-02 (agente)."
```
Expected: commit criado.

---

### Task 17: Validação end-to-end com `.env` real (depende do usuário)

**Description:** Esta task valida o pipeline contra Supabase real. **Requer que o usuário tenha criado `.env` com credenciais válidas (rotacionadas).**

- [ ] **Step 1: Confirmar com o usuário que o `.env` está preenchido**

Pergunte: "Você criou o `.env` na raiz com as credenciais novas (rotacionadas)?" Se não, instruir: `cp .env.example .env` e preencher os valores.

- [ ] **Step 2: Validar conexão dbt no host**

```bash
uv run --package transform dbt debug --project-dir transform --profiles-dir transform
```
Expected: `All checks passed!` e `Connection test: [OK connection ok]`. Se falhar com erro de credencial, parar e revisar `.env`.

- [ ] **Step 3: Rodar EL no host**

```bash
uv run --package extract_load python -m extract_load
```
Expected: logs INFO listando 4 tabelas extraídas e carregadas, com contagens. Exit code 0. **Nenhum log deve conter senha/key em texto puro.**

- [ ] **Step 4: Rodar T no host**

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform
```
Expected: bronze (4 views) + silver (4 tables) + gold (3 tables) construídos. `Completed successfully`.

- [ ] **Step 5: Rodar testes de qualidade do dbt (se existirem)**

```bash
uv run --package transform dbt test --project-dir transform --profiles-dir transform
```
Expected: `PASS` em todos (ou `Nothing to do` se não houver testes ainda). Não deve haver `FAIL`.

- [ ] **Step 6: Rodar pipeline completo via Docker**

```bash
docker compose run --rm extract
docker compose run --rm dbt run
```
Expected: mesma saída do host (extracted/loaded/Completed). Confirma que o `.env` está sendo injetado corretamente nos containers.

- [ ] **Step 7: Conferir que `.env` NÃO entrou nas imagens**

```bash
docker run --rm --entrypoint sh projeto-elt-extract:latest -c 'ls -la /app/.env 2>&1' | head -2
docker run --rm --entrypoint sh projeto-elt-dbt:latest -c 'ls -la /app/.env 2>&1' | head -2
```
Expected: ambos retornam `ls: cannot access '/app/.env': No such file or directory`. Confirma que `.dockerignore` cumpriu seu papel.

- [ ] **Step 8: Conferir log do extract não vaza segredos**

```bash
docker compose run --rm extract 2>&1 | grep -iE "(password|secret|key)" | head -5 || echo "no secrets in logs"
```
Expected: `no secrets in logs`. Se aparecer linha contendo valor de credencial em texto puro, **PARAR e investigar**.

- [ ] **Step 9: Push final (opcional, perguntar ao usuário)**

```bash
git log --oneline -10
```
Expected: ver os últimos commits da reorganização. Se o usuário quiser fazer `git push`, **perguntar antes** — não fazer push automaticamente.

---

## Self-Review (run before handing off)

**Spec coverage:**
- ✅ Estrutura `extract_load/` + `transform/` (T2/T3/T6).
- ✅ uv workspace com lockfile único (T5/T6).
- ✅ Dockerfile EL + Dockerfile T + docker-compose (T11/T13/T14).
- ✅ `transform/profiles.yml` versionado lendo via `env_var()` (T12).
- ✅ Variáveis separadas no `.env`, com `.env.example` (T5).
- ✅ Reescrita modular do EL (config/extract/load/__main__) com TDD (T7/T8/T9/T10).
- ✅ ruff + pytest configurados na raiz (T5/T10).
- ✅ Tests mínimos (1 por módulo) (T7/T8/T9).
- ✅ `.gitignore` ajustado (T4).
- ✅ Delete do `data_lake_connect.py` antigo (T2).
- ✅ Atualização de CLAUDE.md (T16).
- ✅ README mínimo (T15).
- ✅ `.dockerignore` bloqueia `.env` (T5).
- ✅ Validação host + Docker (T17).

**Placeholder scan:** Nenhum "TODO/TBD/implement later". Todo código é literal e completo.

**Type consistency:**
- `Settings` definido em config.py, importado consistentemente em extract.py/load.py/__main__.py/tests.
- `TABELAS` definido em config.py, importado em extract.py.
- `ExtractError` definido em extract.py, importado em __main__.py.
- `LoadError` definido em load.py, importado em __main__.py.
- Assinaturas: `extract(settings: Settings) -> dict[str, pd.DataFrame]`; `load(dfs: dict[str, pd.DataFrame], settings: Settings) -> None`.
- Variáveis de env: nomes consistentes em `.env.example`, `config.py`, `profiles.yml`, `CLAUDE.md`.

---

## Notas para o executor

1. **Nunca imprima** valores de variáveis do `.env` em output, mesmo durante debug. Use `head` em error messages cuidadosamente.
2. Se um teste falhar de forma inesperada, parar e investigar — não "ajustar o teste para passar".
3. Cada task tem commit no final. Se autorizado a commitar, fazer. Se não, agrupar em commit final no fim.
4. Se o `uv sync` da T6 falhar por dependência, revisar versions nos pyproject.tomls antes de relaxar pins.
5. T17 depende do usuário ter `.env` preenchido com credenciais válidas. Se ele não tiver, parar antes do Step 2 e instruir.
6. **Em qualquer momento** que aparecer credencial em log/output não esperado, **PARAR** e reportar — não tentar limpar/ocultar manualmente.


Nota posterior: a camada Gold foi refinada para `gold/dimensional/` e `gold/marts/<setor>/`, mantendo os marts finais com prefixo `gold_*`.
