# Reorganização do projeto ELT — Design

**Data:** 2026-04-28
**Escopo:** apenas reorganização estrutural e configurações iniciais. Cases 01 (dashboard) e 02 (agente Telegram) permanecem fora de escopo.

---

## 1. Contexto

### 1.1 Estado atual

Pipeline ELT funcional com duas pastas:
- `extract_python/` (untracked no git): script monolítico `data_lake_connect.py` faz E + L (S3 → PostgreSQL).
- `ecommerce/` (versionado): projeto dbt com camadas Bronze/Silver/Gold.

Stack: Python (boto3, pandas, sqlalchemy, psycopg2), Supabase Storage (S3-compatible), Supabase PostgreSQL, dbt-core + dbt-postgres.

### 1.2 Problemas identificados

1. **Credenciais hardcoded em texto puro** dentro de `extract_python/data_lake_connect.py`: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY (Supabase Storage), e DATABASE_URL com senha do PostgreSQL. O arquivo é untracked, então não há comprometimento via git, mas as credenciais estão no disco em texto puro.
2. **Sem gestão de dependências moderna**: existe apenas `.venv/` criada com pip+venv, sem `pyproject.toml` nem lockfile.
3. **Sem containerização**: pipeline depende de venv local funcional na máquina do dev.
4. **Profile dbt fora do repo** (`~/.dbt/profiles.yml`): exige passo manual em cada máquina.
5. **Nomes de pasta não refletem o papel**: `extract_python` descreve linguagem (não etapa); `ecommerce` descreve domínio (não etapa).

### 1.3 Objetivos

- Reorganizar pastas para refletir explicitamente as etapas ELT.
- Centralizar segredos em `.env` único, com defesa em camadas contra vazamento.
- Adotar `uv` como gerenciador de dependências, em workspace que isola E+L da T.
- Containerizar todo o pipeline (Docker + docker-compose).
- Refatorar o script monolítico em módulos com responsabilidade única, logging e tratamento de erros.
- Configurar lint (ruff) e testes mínimos (pytest) para o módulo Python.

### 1.4 Não-objetivos

- Modificar lógica de transformação dos modelos dbt.
- Criar arquivos dos cases 01 e 02.
- Configurar CI/CD, pre-commit, mypy, coverage.
- Subir PostgreSQL local em Docker.
- Adicionar orquestrador (Airflow, Prefect, Dagster).

### 1.5 Pré-requisito de segurança (responsabilidade do usuário)

**Antes da implementação**, o usuário rotacionará as credenciais expostas no Supabase:
- Regenerar S3 access keys.
- Trocar a senha do banco PostgreSQL.

A nova reorganização **não lê nem copia** os valores antigos: os módulos novos serão escritos a partir da estrutura/lógica do script antigo, sem reproduzir nenhum literal de credencial.

---

## 2. Decisões fundamentais (consolidadas)

| # | Decisão | Alternativa rejeitada | Motivo |
|---|---|---|---|
| 1 | Refatorar script monolítico em módulos com logging e tratamento de erros | Apenas substituir literais por env vars | Reescrita era esperada; modularidade habilita testes |
| 2 | Estrutura: `extract_load/` + `transform/` | Manter `extract_python/` + `ecommerce/`; ou src-layout único | Nomes refletem etapas ELT; baixo custo de rename |
| 3 | uv workspace com 3 `pyproject.toml` (raiz + 2 pacotes) e lockfile único | Único `pyproject.toml` com optional groups | Permite Docker images independentes; deps isoladas |
| 4 | Docker: 2 Dockerfiles + docker-compose, banco remoto Supabase | Apenas extract dockerizado; ou +PostgreSQL local | Pipeline T precisa estar containerizada também; PG local é escopo creep |
| 5 | `transform/profiles.yml` versionado, lendo via `env_var()` | Manter `~/.dbt/profiles.yml` externo | Onboarding = `cp .env.example .env`; funciona igual no host e no Docker |
| 6 | Variáveis separadas no `.env` (host/port/user/password/db) | `DATABASE_URL` único | Facilita `profiles.yml` do dbt e validações no Python |
| 7 | Python 3.11, logging stdlib, pydantic-settings | 3.10/3.12; structlog/loguru; os.getenv | 3.11 é estável e amplamente suportado; stdlib + pydantic-settings cobrem o necessário sem deps extras |
| 8 | ruff (lint+format) com regras incluindo bandit (`S`) | Sem lint, ou black+flake8+isort separados | Defesa automatizada contra hardcoded secrets; uma ferramenta só |
| 9 | `tests/` mínimo: 3 testes (1 por módulo) | Sem testes; ou cobertura completa | Ancora design testável durante a reescrita; não vira escopo creep |
| 10 | Manter `name: ecommerce` e `profile: ecommerce` no `dbt_project.yml` | Renomear para `transform` | O nome dbt é semântico (domínio), não estrutural |

---

## 3. Arquitetura

### 3.1 Estrutura de pastas alvo

```
projeto-pipeline-ELT-engenharia-supabase-dbt/
│
├── extract_load/                    # Pacote Python: etapas E + L
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── src/
│   │   └── extract_load/
│   │       ├── __init__.py
│   │       ├── __main__.py          # entrypoint: python -m extract_load
│   │       ├── config.py            # carrega/valida .env (pydantic-settings)
│   │       ├── extract.py           # S3 → dict[str, DataFrame]
│   │       └── load.py              # dict[str, DataFrame] → PostgreSQL
│   └── tests/
│       ├── test_config.py
│       ├── test_extract.py
│       └── test_load.py
│
├── transform/                       # Pacote dbt: etapa T (renomeado de ecommerce/)
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── dbt_project.yml              # intocado
│   ├── profiles.yml                 # NOVO — versionado, lê env_var()
│   ├── PRD-dbt.md                   # movido junto
│   ├── models/
│   │   ├── _sources.yml             # intocado
│   │   ├── bronze/                  # 4 SQLs intocados
│   │   ├── silver/                  # 4 SQLs intocados
│   │   └── gold/
│   │       ├── sales/
│   │       │   └── gold_sales_vendas_temporais.sql
│   │       ├── customer_success/
│   │       │   └── gold_customer_success_clientes_segmentacao.sql
│   │       └── pricing/
│   │           └── gold_pricing_precos_competitividade.sql
│   ├── analyses/   seeds/   macros/   snapshots/   tests/
│   ├── target/                      # gitignored
│   ├── logs/                        # gitignored
│   └── dbt_packages/                # gitignored
│
├── docker-compose.yml               # NOVO
├── pyproject.toml                   # NOVO — workspace + ruff + pytest
├── uv.lock                          # NOVO — lockfile único
├── .env.example                     # NOVO — template (sem segredos)
├── .env                             # gitignored — segredos reais
├── .gitignore                       # ATUALIZADO
├── .dockerignore                    # NOVO
├── .python-version                  # NOVO — pin 3.11
├── README.md                        # NOVO — quickstart
├── CLAUDE.md                        # ATUALIZADO
└── .llm/                            # intocada (fora de escopo)
```

### 3.2 Fluxo de dados

```
S3 Bucket (Supabase Storage)
  [vendas, clientes, produtos, preco_competidores].parquet
         │
         ▼
extract_load (módulo Python)
  config.py     → valida .env (pydantic-settings, SecretStr)
  extract.py    → boto3 baixa Parquet → dict[str, pd.DataFrame]
  load.py       → SQLAlchemy + pandas to_sql → schema public
         │
         ▼
PostgreSQL (Supabase) — schema public (raw)
         │
         ▼
transform (projeto dbt)
  bronze/   → views (cópia exata do raw)
  silver/   → tables (limpeza, dimensões temporais, calculos)
  gold/     → tables agregadas em 3 schemas:
              public_gold_sales.gold_sales_vendas_temporais
              public_gold_cs.gold_customer_success_clientes_segmentacao
              public_gold_pricing.gold_pricing_precos_competitividade
```

---

## 4. Componentes — detalhamento

### 4.1 Pacote `extract_load/`

**Responsabilidade:** etapas E e L do pipeline. Lê 4 arquivos Parquet do S3 e carrega no schema `public` do PostgreSQL, sem transformação.

**Módulos:**

- **`config.py`** — classe `Settings(BaseSettings)` (pydantic-settings) com:
  - Postgres: `postgres_host`, `postgres_port` (default 5432), `postgres_db`, `postgres_user`, `postgres_password` (`SecretStr`), `postgres_schema` (default `"public"`), `postgres_sslmode` (default `"require"`).
  - S3: `s3_endpoint_url`, `s3_region`, `s3_access_key_id` (`SecretStr`), `s3_secret_access_key` (`SecretStr`), `s3_bucket`.
  - Logging: `log_level` (default `"INFO"`).
  - Constante `TABELAS = ("vendas", "clientes", "produtos", "preco_competidores")`.

- **`extract.py`** — função `extract(settings: Settings) -> dict[str, pd.DataFrame]`:
  - Cria cliente boto3.
  - Para cada tabela em `TABELAS`: baixa Parquet, converte para DataFrame.
  - Loga INFO por tabela com contagem de linhas.
  - Levanta `ExtractError` em falha de S3 (com contexto: qual tabela).

- **`load.py`** — função `load(dfs: dict[str, pd.DataFrame], settings: Settings) -> None`:
  - Constrói URL de conexão a partir de variáveis separadas.
  - Cria SQLAlchemy `Engine`.
  - Para cada DataFrame: `to_sql(if_exists="replace", schema=...)`.
  - Verificação final: `SELECT COUNT(*)` por tabela e log INFO.
  - `engine.dispose()` em `finally`.
  - Levanta `LoadError` em falha (com contexto).

- **`__main__.py`** — orquestra `Settings()` → `setup_logging()` → `extract()` → `load()`. Captura erros tipados, retorna exit code 0/1.

**Logging:**
- Stdlib `logging`. Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`. Saída: stdout. Nunca loga `Settings` inteiro nem URL de conexão crua.

**Comando:**
- Host: `uv run --package extract_load python -m extract_load`
- Docker: `docker compose run --rm extract`

**Dependências (`extract_load/pyproject.toml`):**
- `boto3>=1.34`, `pandas>=2.2`, `pyarrow>=15.0`, `sqlalchemy>=2.0`, `psycopg2-binary>=2.9`, `python-dotenv>=1.0`, `pydantic-settings>=2.4`.
- Dev: `pytest>=8.0`.
- Build backend: hatchling.

**Testes (`extract_load/tests/`):**
- `test_config.py`: env completo → instancia OK; falta `POSTGRES_PASSWORD` → `ValidationError`; `repr(settings)` não vaza valores de `SecretStr`.
- `test_extract.py`: boto3 mockado retornando bytes Parquet → `extract()` devolve dict com 4 chaves esperadas, cada valor é DataFrame não vazio.
- `test_load.py`: SQLAlchemy `sqlite:///:memory:`; cria DataFrame de exemplo, chama `load()`, verifica `SELECT COUNT(*)`.

### 4.2 Pacote `transform/`

**Responsabilidade:** etapa T (dbt). Lógica de transformação intocada.

**Mudanças apenas em infraestrutura:**

| Arquivo | Ação |
|---|---|
| `ecommerce/` (pasta) | `git mv` → `transform/` |
| `dbt_project.yml` | intocado |
| `models/**/*.sql`, `_sources.yml`, `PRD-dbt.md` | intocados |
| `profiles.yml` | NOVO — versionado, lê via `env_var()` |
| `pyproject.toml` | NOVO — declara dbt-core, dbt-postgres |
| `Dockerfile` | NOVO — imagem do serviço dbt |
| `target/`, `logs/`, `dbt_packages/` | gitignored, deletados antes do commit |

**`transform/profiles.yml`:**

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

**Notas Supabase:**
- Usar **session pooler** (porta 5432). Não usar transaction pooler (6543) com dbt.
- `POSTGRES_USER` no Supabase pooler tem formato `postgres.{project_ref}`.

**Dependências (`transform/pyproject.toml`):**
- `dbt-core>=1.8,<1.10`, `dbt-postgres>=1.8,<1.10`.
- Build backend: hatchling.

**Comandos dbt:**
- Host: `uv run --package transform dbt <subcomando> --project-dir transform --profiles-dir transform`
- Docker: `docker compose run --rm dbt <subcomando>` (com `DBT_PROJECT_DIR` e `DBT_PROFILES_DIR` exportados na imagem).

### 4.3 uv workspace + ruff + pytest

**`pyproject.toml` da raiz:**

```toml
[project]
name = "projeto-pipeline-elt"
version = "0.1.0"
description = "Pipeline ELT: S3 → PostgreSQL → dbt (Bronze/Silver/Gold)"
requires-python = ">=3.11"

[tool.uv.workspace]
members = ["extract_load", "transform"]

[dependency-groups]
dev = ["ruff>=0.6", "pytest>=8.0"]

[tool.ruff]
target-version = "py311"
line-length = 100
extend-exclude = ["transform/target", "transform/dbt_packages", "transform/logs"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "S", "SIM", "RUF"]

[tool.ruff.lint.per-file-ignores]
"**/tests/**" = ["S101"]

[tool.pytest.ini_options]
testpaths = ["extract_load/tests"]
addopts = "-ra --strict-markers"
```

**Regras ruff (motivação):**
- `S` (bandit) — defesa contra hardcoded secrets.
- `B` (bugbear) — anti-patterns sutis.
- `I` (isort) — imports ordenados.
- `UP` (pyupgrade) — sintaxe moderna 3.11+.
- Demais: pycodestyle/pyflakes/naming/simplify.

**`.python-version`** (raiz): `3.11`. Versionado.

**`uv.lock`**: gerado por `uv sync`/`uv lock`, único na raiz, versionado.

**Workflow:**

```bash
# Setup inicial
rm -rf .venv
uv sync
cp .env.example .env

# Dia a dia
uv run --package extract_load python -m extract_load
uv run --package transform dbt run --project-dir transform --profiles-dir transform
uv run pytest
uv run ruff check
uv run ruff format
```

### 4.4 Docker

**Estratégia:** 2 Dockerfiles multi-stage com a imagem oficial do uv. `docker-compose.yml` na raiz orquestra dois serviços (`extract`, `dbt`). Banco é remoto (Supabase) — sem PostgreSQL no compose.

**`extract_load/Dockerfile`** (multi-stage):
- Builder: `python:3.11-slim` + uv via `COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv`.
- Copia metadata (`pyproject.toml`, `uv.lock`, `.python-version`, ambos pacotes' `pyproject.toml`).
- `uv sync --frozen --no-dev --package extract_load` com cache mount.
- Copia código depois (preserva cache de deps em mudanças de código).
- Runtime: `python:3.11-slim` + venv copiada + usuário não-root + `ENTRYPOINT ["python", "-m", "extract_load"]`.

**`transform/Dockerfile`** (mesma estrutura):
- `--package transform`.
- Runtime exporta `DBT_PROFILES_DIR=/app/transform`, `DBT_PROJECT_DIR=/app/transform`.
- `WORKDIR /app/transform`.
- `ENTRYPOINT ["dbt"]`, `CMD ["--help"]` — permite `docker compose run --rm dbt run`.

**`docker-compose.yml` (raiz):**

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
    # OPCIONAL — descomentar para persistir artefatos do dbt:
    # volumes:
    #   - ./transform/target:/app/transform/target
    #   - ./transform/logs:/app/transform/logs
```

**`.dockerignore` (raiz):**

```
.git
.gitignore
.venv
__pycache__
*.pyc
.pytest_cache
.ruff_cache
.mypy_cache
.env
.env.*
!.env.example
transform/target
transform/logs
transform/dbt_packages
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

**Garantias:**
- `.env` listado em `.dockerignore` → nunca entra na imagem.
- Imagens rodam como usuário não-root.
- Multi-stage → imagem final ~250MB sem o uv binary nem cache de build.

**Comandos:**

```bash
docker compose build
docker compose run --rm extract
docker compose run --rm dbt debug
docker compose run --rm dbt run
docker compose run --rm dbt test
```

### 4.5 `.env.example` e gestão de segredos

**`.env.example` (raiz, versionado):** template completo com placeholders (`CHANGE_ME`, `YOUR_PROJECT_REF`) e comentários apontando onde encontrar cada valor no Supabase Console. Variáveis cobertas:

- Postgres: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_SCHEMA`, `POSTGRES_SSLMODE`.
- S3 / Supabase Storage: `S3_ENDPOINT_URL`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET`.
- Logging: `LOG_LEVEL`.

**Regras invioláveis:**
- Nunca incluir valor real, mesmo que pareça fake.
- Senhas/keys → literal `CHANGE_ME`.
- IDs de projeto → `YOUR_PROJECT_REF`.

**Tratamento do arquivo `data_lake_connect.py` antigo:**
- Será **deletado** durante o rename `extract_python/` → `extract_load/`.
- Os módulos novos serão escritos a partir da estrutura do antigo, **sem copiar literais de credenciais**.
- Como o arquivo é untracked, deletar não afeta histórico do git.

**Limpeza adicional (responsabilidade do usuário):**
- Rotacionar credenciais no Supabase.
- Verificar cópias do arquivo em backups locais (lixeira, VS Code Local History, etc.).

**Defesa em camadas contra vazamento:**

| Camada | Proteção |
|---|---|
| Git | `.env`, `.env.*` (exceto `.env.example`) ignorados |
| Docker imagem | `.env` em `.dockerignore` |
| Docker runtime | `.env` injetado por `env_file:` no compose |
| Logs Python | `SecretStr` mascara `repr/str/traceback` |
| Logs dbt | dbt mascara `password` nativamente |
| Lint | ruff regra `S` (bandit) detecta hardcoded secrets |

### 4.6 README, CLAUDE.md, .gitignore

**`README.md` (novo, raiz):** quickstart de ~50 linhas. Stack, estrutura, setup local, comandos host, comandos Docker, bloco curto sobre segurança. Aponta para `CLAUDE.md` e `.llm/database.md` para detalhes.

**`CLAUDE.md` (atualizar):**
- Substituir paths `ecommerce/` → `transform/`.
- Substituir comandos `cd ecommerce; dbt ...` por `uv run --package transform dbt ... --project-dir transform --profiles-dir transform`.
- Substituir `python extract_python/data_lake_connect.py` por `uv run --package extract_load python -m extract_load`.
- Atualizar seção "Configuração de Ambiente": `transform/profiles.yml` versionado, `.env` único na raiz.
- Atualizar diagrama de fluxo: `extract_python/data_lake_connect.py` → `extract_load (módulo Python)`.
- Adicionar seção "Comandos uv".
- Adicionar seção "Comandos Docker".
- Adicionar seção "Lint e testes" (ruff, pytest).
- **Manter intactas** as seções "Dashboard (case-01)" e "Agente de Relatórios Diários (case-02)".

**`.gitignore` (atualizar):**
- **Remover** a linha `profiles.yml` (versionamos `transform/profiles.yml` agora).
- Adicionar comentário explicativo no lugar.
- Demais regras já estão adequadas (incluindo `.env`, `.venv/`, `target/`, `dbt_packages/`, `logs/`, `.ruff_cache/`).

---

## 5. Plano de execução (alto nível)

A sequência abaixo será detalhada em plano de implementação na próxima etapa. Aqui apenas a ordem lógica:

1. **Pré-requisito (usuário):** rotacionar credenciais no Supabase.
2. **Backup mental:** confirmar que `extract_python/` é untracked (sem perda de histórico ao deletar).
3. **Renomes e deletes de pasta:**
   - `git mv ecommerce transform`.
   - Apagar `extract_python/data_lake_connect.py` e `extract_python/`.
4. **Criar arquivos de configuração da raiz:**
   - `pyproject.toml` (workspace + ruff + pytest).
   - `.python-version`.
   - `.env.example`.
   - `.dockerignore`.
   - `README.md`.
5. **Atualizar `.gitignore`** (remover `profiles.yml`).
6. **Criar `extract_load/`:**
   - `pyproject.toml`, `Dockerfile`.
   - `src/extract_load/{__init__,__main__,config,extract,load}.py`.
   - `tests/{test_config,test_extract,test_load}.py`.
7. **Criar arquivos novos em `transform/`:**
   - `pyproject.toml`.
   - `Dockerfile`.
   - `profiles.yml`.
8. **Criar `docker-compose.yml`** na raiz.
9. **Atualizar `CLAUDE.md`** (paths, comandos, profile).
10. **Validar:**
    - `uv sync` cria `.venv/` na raiz.
    - `uv run pytest` (3 testes verdes).
    - `uv run ruff check` (sem violações).
    - `docker compose build` (ambas imagens constroem).
    - Após o usuário criar `.env` com credenciais novas:
      - `uv run --package extract_load python -m extract_load` executa EL.
      - `uv run --package transform dbt debug --project-dir transform --profiles-dir transform` conecta.
      - `uv run --package transform dbt run --project-dir transform --profiles-dir transform` executa T.
      - Mesma validação via `docker compose run --rm extract` e `docker compose run --rm dbt run`.
11. **Commit** das mudanças.

---

## 6. Riscos e mitigações

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Credenciais antigas continuam ativas após reorganização | Alta se usuário não rotacionar | Pré-requisito explícito; spec aponta a urgência |
| Cópias do `data_lake_connect.py` antigo persistem em backups locais | Média | Item de checklist para o usuário; limpeza fora do escopo do código |
| Alguém adiciona segredo em `transform/profiles.yml` por engano | Baixa | Diff em PR; ruff cobre Python; review humano cobre YAML |
| Versão dbt fora do range (1.8–1.9) introduz breaking change | Baixa | Pin `>=1.8,<1.10`; `uv lock --upgrade` controlado |
| Build Docker quebra por mudança em `uv.lock` | Baixa | `uv sync --frozen` no Dockerfile força match exato; lockfile versionado |
| Supabase pooler timeouts em runs longos do dbt | Baixa | `keepalives_idle: 0` no profiles.yml; usar session pooler (5432), não transaction (6543) |
| Pasta `.venv/` antiga (pip+venv) entra em conflito com nova (uv) | Média | Comando explícito `rm -rf .venv` antes de `uv sync`, documentado no README |

---

## 7. Fora de escopo (recapitulação)

- Cases 01 (dashboard Streamlit) e 02 (agente Telegram).
- Pasta `.llm/` (intocada).
- CI/CD, pre-commit, mypy, coverage.
- PostgreSQL local em docker-compose.
- Refatoração de modelos dbt.
- Migrações de schema, seeds, snapshots.
- Orquestrador (Airflow/Prefect/Dagster).
- Auditoria/observabilidade além de logs em stdout.


Nota posterior: a camada Gold foi refinada para `gold/dimensional/` e `gold/marts/<setor>/`, mantendo os marts finais com prefixo `gold_*`.
