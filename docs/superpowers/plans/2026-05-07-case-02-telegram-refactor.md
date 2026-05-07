# Refatoração Case 02 (Agente Telegram) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refatorar `.llm/case-02-telegram/agente.py` e `db.py` em 3 arquivos modulares (`db.py`, `agente.py`, `bot.py`), corrigir o bug de schemas, eliminar fontes de vazamento de credencial e implementar persistência real do `CHAT_ID`.

**Architecture:** 3 arquivos. `Settings` (pydantic-settings + SecretStr) no topo de `agente.py` e reusado por `bot.py`. `db.py` recebe Settings por parâmetro. `bot.py` é o único módulo que escreve no `.env` da raiz.

**Tech Stack:** Python 3.11+, pydantic-settings, anthropic SDK, python-telegram-bot v20+, sqlalchemy, psycopg2-binary, pandas, tabulate.

**Spec:** `docs/superpowers/specs/2026-05-07-case-02-telegram-refactor-design.md`

**Notas de verificação:** Esse case não tem infra pytest. Verificação por **smoke tests** via `python -c "..."` e execução real dos entry points. Cada tarefa tem critério de aceite explícito.

---

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `.llm/case-02-telegram/db.py` | Modificar | engine + execute_query (SELECT/WITH) |
| `.llm/case-02-telegram/agente.py` | Modificar | Settings + SCHEMA + chat + gerar_relatorio + enviar_telegram + main |
| `.llm/case-02-telegram/bot.py` | Criar | handlers + salvar_chat_id + polling |
| `.llm/case-02-telegram/requirements.txt` | Criar | dependências do case |
| `.gitignore` (raiz) | Modificar | adicionar `.llm/case-02-telegram/relatorio_*.md` |
| `.env` (raiz) | Modificar (manual) | adicionar `TELEGRAM`, `ANTHROPIC_API_KEY`, etc. (usuário preenche) |

---

## Task 1: Setup de arquivos auxiliares

**Files:**
- Create: `.llm/case-02-telegram/requirements.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Criar `requirements.txt`**

Conteúdo de `.llm/case-02-telegram/requirements.txt`:
```
anthropic>=0.40
python-telegram-bot>=20
sqlalchemy>=2.0
psycopg2-binary>=2.9
pandas>=2.0
tabulate>=0.9
pydantic>=2.0
pydantic-settings>=2.0
```

- [ ] **Step 2: Adicionar relatorios ao `.gitignore` da raiz**

Editar `.gitignore` na raiz adicionando após a seção `# Environment / secrets`:
```
# Case 02 — relatórios gerados
.llm/case-02-telegram/relatorio_*.md
```

- [ ] **Step 3: Verificar gitignore**

Run:
```bash
touch .llm/case-02-telegram/relatorio_2026-05-07.md
git status --short .llm/case-02-telegram/
rm .llm/case-02-telegram/relatorio_2026-05-07.md
```
Expected: `relatorio_2026-05-07.md` NÃO aparece em `git status` (está ignorado).

- [ ] **Step 4: Commit**

```bash
git add .llm/case-02-telegram/requirements.txt .gitignore
git commit -m "build: adiciona requirements e gitignore do case-02"
```

---

## Task 2: Refatorar `db.py`

**Files:**
- Modify: `.llm/case-02-telegram/db.py`

- [ ] **Step 1: Substituir conteúdo de `db.py`**

Conteúdo completo:
```python
import pandas as pd
from pydantic import SecretStr
from sqlalchemy import Engine, create_engine, text


def get_engine(postgres_url: SecretStr) -> Engine:
    return create_engine(postgres_url.get_secret_value())


def execute_query(sql: str, postgres_url: SecretStr) -> pd.DataFrame:
    sql_clean = sql.strip().upper()
    if not (sql_clean.startswith("SELECT") or sql_clean.startswith("WITH")):
        raise ValueError("Apenas SELECT/WITH são permitidos.")

    engine = get_engine(postgres_url)
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)
```

Notas:
- Recebe `postgres_url: SecretStr` direto (não a `Settings` inteira) — interface mínima, evita import circular com `agente.py`.
- Sem `os.getenv`. Sem fallback `profiles.yml`. Sem `import yaml`.
- `Engine` importado para tipagem do retorno.

- [ ] **Step 2: Smoke test — apenas SELECT/WITH passam validação**

Run:
```bash
cd .llm/case-02-telegram
python -c "
from pydantic import SecretStr
from db import execute_query
try:
    execute_query('DROP TABLE x', SecretStr('postgresql://fake'))
    print('FAIL: deveria ter levantado ValueError')
except ValueError as e:
    print('OK validação:', e)
"
```
Expected output: `OK validação: Apenas SELECT/WITH são permitidos.`

- [ ] **Step 3: Commit**

```bash
git add .llm/case-02-telegram/db.py
git commit -m "refactor(case-02): db.py recebe SecretStr e remove fallback profiles.yml"
```

---

## Task 3: `agente.py` — Settings + constantes

Reescreveremos `agente.py` em etapas. Começamos pelo bloco de Settings, SCHEMA, TOOL e QUERIES_RELATORIO. Tudo em um único arquivo final, mas construído incrementalmente.

**Files:**
- Modify: `.llm/case-02-telegram/agente.py`

- [ ] **Step 1: Reescrever `agente.py` com Settings + constantes (sem funções ainda)**

Substituir todo o conteúdo de `agente.py` por:
```python
"""Agente Telegram — chat livre, relatório executivo e envio direto via API HTTP."""

from __future__ import annotations

import logging
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import anthropic
import pandas as pd
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from db import execute_query

# ── Settings ─────────────────────────────────────────────────────────
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    telegram: SecretStr
    anthropic_api_key: SecretStr
    postgres_url: SecretStr
    chat_id: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"


# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


# ── Constantes ───────────────────────────────────────────────────────
MAX_ITERACOES_TOOL = 10
TELEGRAM_MAX_CHARS = 4096

SCHEMA = """
Tabelas disponíveis no banco PostgreSQL:

1. public_gold_sales.gold_sales_vendas_temporais
   Colunas: data_venda (DATE), ano_venda, mes_venda, dia_venda, dia_semana_nome (VARCHAR),
            hora_venda, receita_total (NUMERIC), quantidade_total, total_vendas,
            total_clientes_unicos, ticket_medio (NUMERIC)

2. public_gold_cs.gold_customer_success_clientes_segmentacao
   Colunas: cliente_id (VARCHAR), nome_cliente, estado (VARCHAR(2)), receita_total (NUMERIC),
            total_compras, ticket_medio (NUMERIC), primeira_compra (DATE), ultima_compra (DATE),
            segmento_cliente (VIP | TOP_TIER | REGULAR), ranking_receita (INTEGER)

3. public_gold_pricing.gold_pricing_precos_competitividade
   Colunas: produto_id (VARCHAR), nome_produto, categoria, marca, nosso_preco (NUMERIC),
            preco_medio_concorrentes, preco_minimo_concorrentes, preco_maximo_concorrentes,
            total_concorrentes, diferenca_percentual_vs_media (NUMERIC),
            diferenca_percentual_vs_minimo (NUMERIC),
            classificacao_preco (MAIS_CARO_QUE_TODOS | ACIMA_DA_MEDIA | NA_MEDIA | ABAIXO_DA_MEDIA | MAIS_BARATO_QUE_TODOS),
            receita_total (NUMERIC), quantidade_total
"""

TOOL = {
    "name": "executar_sql",
    "description": "Executa query SQL SELECT no banco PostgreSQL do e-commerce.",
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "Query SQL SELECT para executar.",
            }
        },
        "required": ["sql"],
    },
}

QUERIES_RELATORIO: dict[str, str] = {
    "vendas": """
        SELECT data_venda, dia_semana_nome,
            SUM(receita_total) AS receita,
            SUM(total_vendas) AS vendas,
            SUM(total_clientes_unicos) AS clientes,
            AVG(ticket_medio) AS ticket_medio
        FROM public_gold_sales.gold_sales_vendas_temporais
        GROUP BY data_venda, dia_semana_nome
        ORDER BY data_venda DESC
        LIMIT 7
    """,
    "clientes": """
        SELECT segmento_cliente,
            COUNT(*) AS total_clientes,
            SUM(receita_total) AS receita_total,
            AVG(ticket_medio) AS ticket_medio_avg,
            AVG(total_compras) AS compras_avg
        FROM public_gold_cs.gold_customer_success_clientes_segmentacao
        GROUP BY segmento_cliente
        ORDER BY receita_total DESC
    """,
    "pricing": """
        SELECT classificacao_preco,
            COUNT(*) AS total_produtos,
            AVG(diferenca_percentual_vs_media) AS dif_media_pct,
            SUM(receita_total) AS receita_impactada
        FROM public_gold_pricing.gold_pricing_precos_competitividade
        GROUP BY classificacao_preco
        ORDER BY total_produtos DESC
    """,
    "criticos": """
        SELECT nome_produto, categoria, nosso_preco,
            preco_medio_concorrentes,
            diferenca_percentual_vs_media,
            receita_total
        FROM public_gold_pricing.gold_pricing_precos_competitividade
        WHERE classificacao_preco = 'MAIS_CARO_QUE_TODOS'
        ORDER BY diferenca_percentual_vs_media DESC
        LIMIT 10
    """,
}
```

- [ ] **Step 2: Smoke test — Settings carrega do `.env` da raiz**

Pré-requisito: `.env` da raiz tem `TELEGRAM`, `ANTHROPIC_API_KEY`, `POSTGRES_URL` preenchidos (mesmo que com placeholders válidos para teste, ex.: `TELEGRAM=test`, `ANTHROPIC_API_KEY=test`).

Run:
```bash
cd .llm/case-02-telegram
python -c "
from agente import Settings, SCHEMA, QUERIES_RELATORIO
s = Settings()
assert s.anthropic_model == 'claude-sonnet-4-6'
assert 'gold_sales_vendas_temporais' in SCHEMA
assert 'public_gold_cs.gold_customer_success_clientes_segmentacao' in QUERIES_RELATORIO['clientes']
print('OK: Settings carregou e schemas estão corretos')
"
```
Expected: `OK: Settings carregou e schemas estão corretos`

- [ ] **Step 3: Smoke test — Settings falha se variável faltar**

Run:
```bash
cd .llm/case-02-telegram
python -c "
import os
os.environ.pop('ANTHROPIC_API_KEY', None)
# Force vazio mesmo do .env
os.environ['ANTHROPIC_API_KEY'] = ''
"
# Esse teste é informativo; a validação de obrigatórias é via pydantic.
# Mais relevante: confirmar que SecretStr mascara
python -c "
from agente import Settings
s = Settings()
print('repr telegram:', repr(s.telegram))
assert '**' in repr(s.telegram) or 'SecretStr' in repr(s.telegram)
print('OK: SecretStr mascara o valor no repr')
"
```
Expected: `repr` mostra `SecretStr('**********')` ou similar; valor real NÃO aparece.

- [ ] **Step 4: Commit**

```bash
git add .llm/case-02-telegram/agente.py
git commit -m "refactor(case-02): introduz Settings pydantic e corrige schemas Gold"
```

---

## Task 4: `agente.py` — função `chat()` e helper de tool use

**Files:**
- Modify: `.llm/case-02-telegram/agente.py` (apenda funções)

- [ ] **Step 1: Adicionar `_executar_tool_call` e `chat` ao final de `agente.py`**

Anexar ao final de `agente.py` (após o bloco de constantes):
```python
# ── Helpers de tool use ──────────────────────────────────────────────


def _executar_tool_call(block, settings: Settings) -> dict:
    """Executa um tool_use block e retorna o tool_result correspondente."""
    try:
        df = execute_query(block.input["sql"], settings.postgres_url)
        resultado = df.to_markdown(index=False) if not df.empty else "Sem resultados."
    except Exception as e:
        resultado = f"Erro ao executar SQL: {e}"

    return {
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": resultado,
    }


# ── Chat livre ───────────────────────────────────────────────────────


def chat(pergunta: str, settings: Settings) -> str:
    log.info("Chat recebido: %s", pergunta[:80])

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())

    system = (
        "Você é um analista de dados de um e-commerce brasileiro.\n"
        "Responda perguntas usando os dados do banco PostgreSQL.\n"
        "Use a ferramenta executar_sql para consultar os dados necessários.\n"
        "Formate valores monetários em R$. Responda em português.\n"
        "Seja conciso e direto.\n\n"
        + SCHEMA
    )

    messages = [{"role": "user", "content": pergunta}]

    for _ in range(MAX_ITERACOES_TOOL):
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=2048,
            system=system,
            tools=[TOOL],
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "Não consegui gerar uma resposta."

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = [
                _executar_tool_call(block, settings)
                for block in response.content
                if block.type == "tool_use" and block.name == "executar_sql"
            ]
            messages.append({"role": "user", "content": tool_results})

    return "Limite de iterações atingido. Tente reformular a pergunta."
```

- [ ] **Step 2: Smoke test — assinatura de `chat`**

Run:
```bash
cd .llm/case-02-telegram
python -c "
import inspect
from agente import chat, Settings
sig = inspect.signature(chat)
params = list(sig.parameters)
assert params == ['pergunta', 'settings'], f'params errados: {params}'
print('OK: chat(pergunta, settings) ✓')
"
```
Expected: `OK: chat(pergunta, settings) ✓`

- [ ] **Step 3: Commit**

```bash
git add .llm/case-02-telegram/agente.py
git commit -m "feat(case-02): adiciona função chat com tool use no agente"
```

---

## Task 5: `agente.py` — função `gerar_relatorio()`

**Files:**
- Modify: `.llm/case-02-telegram/agente.py` (apenda função)

- [ ] **Step 1: Adicionar `gerar_relatorio` ao final de `agente.py`**

Anexar:
```python
# ── Relatório executivo ──────────────────────────────────────────────


def _executar_queries_relatorio(settings: Settings) -> dict[str, pd.DataFrame]:
    dados = {}
    for nome, sql in QUERIES_RELATORIO.items():
        log.info("Consultando %s...", nome)
        dados[nome] = execute_query(sql, settings.postgres_url)
    return dados


def _montar_prompt_relatorio(dados: dict[str, pd.DataFrame]) -> str:
    return f"""Gere o relatório diário com base nos dados abaixo.

## Dados de Vendas (últimos 7 dias)
{dados["vendas"].to_markdown(index=False)}

## Segmentação de Clientes
{dados["clientes"].to_markdown(index=False)}

## Posicionamento de Preços
{dados["pricing"].to_markdown(index=False)}

## Produtos Críticos (mais caros que todos os concorrentes)
{dados["criticos"].to_markdown(index=False)}

Gere o relatório com 3 seções:
1. Comercial (para o Diretor Comercial)
2. Customer Success (para a Diretora de CS)
3. Pricing (para o Diretor de Pricing)

Comece com um resumo executivo de 3 linhas antes das seções."""


_SYSTEM_RELATORIO = (
    "Você é um analista de dados senior de um e-commerce.\n"
    "Sua função é gerar um relatório executivo diário para 3 diretores.\n"
    "Cada diretor tem necessidades diferentes:\n\n"
    "1. Diretor Comercial: receita, vendas, ticket médio e tendências.\n"
    "2. Diretora de Customer Success: segmentação de clientes, VIPs e riscos.\n"
    "3. Diretor de Pricing: posicionamento de preço vs concorrência e alertas.\n\n"
    "Regras do relatório:\n"
    "- Seja direto e acionável. Cada insight deve sugerir uma ação.\n"
    "- Use números reais dos dados fornecidos.\n"
    "- Formate valores monetários em reais (R$).\n"
    "- Destaque alertas críticos no início.\n"
    "- O relatório deve ter no máximo 1 página por diretor.\n"
    "- Use formato Markdown."
)


def _fallback_markdown(dados: dict[str, pd.DataFrame], erro: Exception) -> str:
    """Fallback se a API do Claude falhar: dados crus em markdown."""
    return (
        f"# Relatório (FALLBACK — Claude indisponível)\n"
        f"Erro: {erro}\n\n"
        f"## Vendas\n{dados['vendas'].to_markdown(index=False)}\n\n"
        f"## Clientes\n{dados['clientes'].to_markdown(index=False)}\n\n"
        f"## Pricing\n{dados['pricing'].to_markdown(index=False)}\n\n"
        f"## Críticos\n{dados['criticos'].to_markdown(index=False)}\n"
    )


def gerar_relatorio(settings: Settings) -> str:
    log.info("Iniciando geração do relatório...")
    dados = _executar_queries_relatorio(settings)

    log.info("Enviando para Claude API...")
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())
    prompt = _montar_prompt_relatorio(dados)

    try:
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=_SYSTEM_RELATORIO,
            messages=[{"role": "user", "content": prompt}],
        )
        relatorio = response.content[0].text
    except Exception as e:
        log.exception("Falha na API do Claude — usando fallback")
        relatorio = _fallback_markdown(dados, e)

    hoje = datetime.now().strftime("%Y-%m-%d")
    arquivo = Path(__file__).parent / f"relatorio_{hoje}.md"
    arquivo.write_text(relatorio, encoding="utf-8")
    log.info("Relatório salvo em: %s", arquivo.name)
    return relatorio
```

- [ ] **Step 2: Smoke test — queries usam schemas corretos**

Run:
```bash
cd .llm/case-02-telegram
python -c "
from agente import QUERIES_RELATORIO
schemas_esperados = [
    'public_gold_sales.gold_sales_vendas_temporais',
    'public_gold_cs.gold_customer_success_clientes_segmentacao',
    'public_gold_pricing.gold_pricing_precos_competitividade',
]
todas = ' '.join(QUERIES_RELATORIO.values())
for s in schemas_esperados:
    assert s in todas, f'schema ausente: {s}'
print('OK: 3 schemas Gold corretos presentes nas queries')
"
```
Expected: `OK: 3 schemas Gold corretos presentes nas queries`

- [ ] **Step 3: Commit**

```bash
git add .llm/case-02-telegram/agente.py
git commit -m "feat(case-02): adiciona gerar_relatorio com fallback se Claude falhar"
```

---

## Task 6: `agente.py` — `enviar_telegram` e `__main__`

**Files:**
- Modify: `.llm/case-02-telegram/agente.py`

- [ ] **Step 1: Adicionar envio Telegram + main standalone**

Anexar ao final de `agente.py`:
```python
# ── Envio Telegram via API HTTP ──────────────────────────────────────


def _split_telegram(texto: str, max_len: int = TELEGRAM_MAX_CHARS) -> list[str]:
    return [texto[i : i + max_len] for i in range(0, len(texto), max_len)]


def _enviar_parte(token: str, chat_id: str, texto: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for parse_mode in ("Markdown", None):
        payload = {"chat_id": chat_id, "text": texto}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        data = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
                if resp.status == 200:
                    return True
        except Exception:
            continue
    return False


def enviar_telegram(
    texto: str,
    settings: Settings,
    chat_id: str | None = None,
) -> None:
    destino = chat_id or settings.chat_id
    if not destino:
        log.warning("CHAT_ID não configurado. Inicie o bot e envie /start primeiro.")
        return

    token = settings.telegram.get_secret_value()
    sucesso_total = True
    for parte in _split_telegram(texto):
        if not _enviar_parte(token, destino, parte):
            log.error("Falha ao enviar parte da mensagem.")
            sucesso_total = False

    if sucesso_total:
        log.info("Mensagem enviada para chat_id=%s", destino)


# ── Main standalone ──────────────────────────────────────────────────


if __name__ == "__main__":
    settings = Settings()
    relatorio = gerar_relatorio(settings)
    print(relatorio)
    if settings.chat_id:
        enviar_telegram(relatorio, settings)
    else:
        log.warning(
            "CHAT_ID ausente — relatório salvo em .md mas não enviado. "
            "Rode bot.py e envie /start no Telegram para registrar."
        )
```

Notas:
- `_enviar_parte` retorna bool: `True` se enviou (Markdown ou texto), `False` caso ambos falhem.
- `# noqa: S310` silencia ruff sobre `urlopen` com URL "dinâmica" (URL é literal, params via POST).

- [ ] **Step 2: Smoke test — split funciona**

Run:
```bash
cd .llm/case-02-telegram
python -c "
from agente import _split_telegram
partes = _split_telegram('a' * 10000)
assert len(partes) == 3
assert all(len(p) <= 4096 for p in partes)
print('OK: split em', len(partes), 'partes ≤ 4096 chars')
"
```
Expected: `OK: split em 3 partes ≤ 4096 chars`

- [ ] **Step 3: Smoke test — Settings falha rápido sem variáveis obrigatórias**

Run:
```bash
cd .llm/case-02-telegram
python -c "
import os
for k in ['TELEGRAM','ANTHROPIC_API_KEY','POSTGRES_URL']:
    os.environ.pop(k, None)
from agente import Settings
try:
    s = Settings(_env_file=None)
    print('FAIL: deveria ter levantado ValidationError')
except Exception as e:
    print('OK: falha rápida -', type(e).__name__)
"
```
Expected: `OK: falha rápida - ValidationError`

Notas: `_env_file=None` desabilita leitura do `.env` para o teste; combinado com `os.environ.pop`, garante que as obrigatórias estejam ausentes.

- [ ] **Step 4: Commit**

```bash
git add .llm/case-02-telegram/agente.py
git commit -m "feat(case-02): adiciona enviar_telegram e entry point standalone"
```

---

## Task 7: Criar `bot.py`

**Files:**
- Create: `.llm/case-02-telegram/bot.py`

- [ ] **Step 1: Criar `bot.py` completo**

Conteúdo de `.llm/case-02-telegram/bot.py`:
```python
"""Bot Telegram — modo interativo (polling). Auto-registra CHAT_ID no .env da raiz."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from agente import (
    ENV_PATH,
    Settings,
    chat,
    enviar_telegram,
    gerar_relatorio,
)

log = logging.getLogger(__name__)


# ── Persistência do CHAT_ID ──────────────────────────────────────────


_CHAT_ID_RE = re.compile(r"^CHAT_ID=.*$", re.MULTILINE)


def salvar_chat_id(chat_id: int, env_path: Path = ENV_PATH) -> None:
    """Atualiza ou anexa CHAT_ID=... no arquivo .env."""
    chat_id_str = str(chat_id)
    nova_linha = f"CHAT_ID={chat_id_str}"

    try:
        if env_path.exists():
            conteudo = env_path.read_text(encoding="utf-8")
        else:
            conteudo = ""

        if _CHAT_ID_RE.search(conteudo):
            atual = _CHAT_ID_RE.search(conteudo).group(0)
            if atual == nova_linha:
                return
            conteudo = _CHAT_ID_RE.sub(nova_linha, conteudo)
        else:
            if conteudo and not conteudo.endswith("\n"):
                conteudo += "\n"
            conteudo += nova_linha + "\n"

        env_path.write_text(conteudo, encoding="utf-8")
        log.info("CHAT_ID=%s salvo no .env", chat_id_str)
    except OSError as e:
        log.error("Falha ao escrever CHAT_ID no .env: %s", e)


# ── Handlers ─────────────────────────────────────────────────────────


async def _enviar_longo(update: Update, texto: str) -> None:
    for i in range(0, len(texto), 4096):
        parte = texto[i : i + 4096]
        try:
            await update.message.reply_text(parte, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(parte)


async def handler_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    salvar_chat_id(update.message.chat_id)
    await update.message.reply_text(
        "Olá! Sou o assistente de dados do e-commerce 📊\n\n"
        "Comandos disponíveis:\n"
        "/relatorio — gera o relatório executivo diário\n\n"
        "Ou faça qualquer pergunta sobre vendas, clientes ou pricing!"
    )


async def handler_relatorio(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    salvar_chat_id(update.message.chat_id)
    await update.message.reply_chat_action(ChatAction.TYPING)
    await update.message.reply_text("Gerando relatório... Aguarde um momento ⏳")
    settings: Settings = _.bot_data["settings"]
    try:
        texto = gerar_relatorio(settings)
        await _enviar_longo(update, texto)
    except Exception as e:
        log.exception("Erro ao gerar relatório")
        await update.message.reply_text(f"Erro ao gerar relatório: {e}")


async def handler_mensagem(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    salvar_chat_id(update.message.chat_id)
    await update.message.reply_chat_action(ChatAction.TYPING)
    settings: Settings = _.bot_data["settings"]
    try:
        resposta = chat(update.message.text, settings)
        await _enviar_longo(update, resposta)
    except Exception as e:
        log.exception("Erro ao processar pergunta")
        await update.message.reply_text(f"Erro ao processar pergunta: {e}")


# ── Entry point ──────────────────────────────────────────────────────


def main() -> None:
    settings = Settings()
    log.info("Iniciando bot Telegram...")

    app = ApplicationBuilder().token(settings.telegram.get_secret_value()).build()
    app.bot_data["settings"] = settings
    app.add_handler(CommandHandler("start", handler_start))
    app.add_handler(CommandHandler("relatorio", handler_relatorio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler_mensagem))

    log.info("Bot rodando! Ctrl+C para parar.")
    app.run_polling()


if __name__ == "__main__":
    main()


# Re-export para uso externo (ex.: `from bot import enviar_telegram` se alguém preferir)
__all__ = ["enviar_telegram", "main", "salvar_chat_id"]
```

Notas:
- `salvar_chat_id` é idempotente: lê, atualiza-ou-anexa, escreve. Idempotência verificada por compare antes de gravar.
- `Settings` injetada em `app.bot_data["settings"]` para handlers acessarem sem reimport.
- `enviar_telegram` continua vivendo em `agente.py`; re-exportado em `__all__` por conveniência.

- [ ] **Step 2: Smoke test — `salvar_chat_id` em arquivo temporário**

Run:
```bash
cd .llm/case-02-telegram
python -c "
import tempfile
from pathlib import Path
from bot import salvar_chat_id

# Caso 1: arquivo sem CHAT_ID — anexa
with tempfile.NamedTemporaryFile('w', suffix='.env', delete=False, encoding='utf-8') as f:
    f.write('FOO=bar\n')
    tmp = Path(f.name)

salvar_chat_id(123, tmp)
conteudo = tmp.read_text(encoding='utf-8')
assert 'CHAT_ID=123' in conteudo
assert 'FOO=bar' in conteudo

# Caso 2: arquivo com CHAT_ID — substitui
salvar_chat_id(456, tmp)
conteudo = tmp.read_text(encoding='utf-8')
assert 'CHAT_ID=456' in conteudo
assert 'CHAT_ID=123' not in conteudo
assert conteudo.count('CHAT_ID=') == 1

# Caso 3: idempotência — chamar com mesmo valor não muda
mtime1 = tmp.stat().st_mtime_ns
salvar_chat_id(456, tmp)
mtime2 = tmp.stat().st_mtime_ns
assert mtime1 == mtime2, 'arquivo foi reescrito sem necessidade'

tmp.unlink()
print('OK: salvar_chat_id — anexa, substitui e é idempotente')
"
```
Expected: `OK: salvar_chat_id — anexa, substitui e é idempotente`

- [ ] **Step 3: Smoke test — bot.py importa sem erro**

Run:
```bash
cd .llm/case-02-telegram
python -c "
import bot
assert hasattr(bot, 'main')
assert hasattr(bot, 'salvar_chat_id')
assert hasattr(bot, 'enviar_telegram')
print('OK: bot.py importa Settings/chat/gerar_relatorio/enviar_telegram de agente')
"
```
Expected: `OK: bot.py importa Settings/chat/gerar_relatorio/enviar_telegram de agente`

- [ ] **Step 4: Commit**

```bash
git add .llm/case-02-telegram/bot.py
git commit -m "feat(case-02): adiciona bot.py com handlers e persistência de CHAT_ID"
```

---

## Task 8: Validação ruff e docs

**Files:**
- Modify: nenhum (validação)

- [ ] **Step 1: Rodar ruff no case**

Run:
```bash
uv run ruff check .llm/case-02-telegram/
uv run ruff format .llm/case-02-telegram/ --check
```
Expected: sem erros. Se `format --check` falhar, rodar `uv run ruff format .llm/case-02-telegram/` e re-checar.

- [ ] **Step 2: Smoke test final — todas as importações públicas resolvem**

Run:
```bash
cd .llm/case-02-telegram
python -c "
from agente import (
    Settings, ENV_PATH, SCHEMA, TOOL, QUERIES_RELATORIO,
    MAX_ITERACOES_TOOL, TELEGRAM_MAX_CHARS,
    chat, gerar_relatorio, enviar_telegram,
)
from bot import main, salvar_chat_id
from db import execute_query, get_engine
assert ENV_PATH.name == '.env'
# ENV_PATH deve apontar para .env DOIS níveis acima da pasta do case
# (case-02-telegram → .llm → raiz/.env)
assert ENV_PATH.parent.name not in ('.llm', 'case-02-telegram'), (
    f'ENV_PATH não está na raiz: {ENV_PATH}'
)
print('OK: APIs públicas alinhadas com o spec; ENV_PATH na raiz')
"
```
Expected: `OK: APIs públicas alinhadas com o spec`

- [ ] **Step 3: Commit (se ruff format aplicou mudanças)**

Se Step 1 fez auto-format:
```bash
git add .llm/case-02-telegram/
git commit -m "style(case-02): aplica ruff format"
```

Caso contrário, pular.

---

## Task 9: Smoke test end-to-end (manual, com `.env` real)

> **Pré-requisito:** `.env` da raiz preenchido com `TELEGRAM`, `ANTHROPIC_API_KEY`, `POSTGRES_URL` reais.

**Files:** nenhum.

- [ ] **Step 1: Rodar `python agente.py` standalone**

Run:
```bash
cd .llm/case-02-telegram
python agente.py
```
Expected:
- Logs: `Iniciando geração do relatório...` → `Consultando vendas...` → `Consultando clientes...` → `Consultando pricing...` → `Consultando criticos...` → `Enviando para Claude API...` → `Relatório salvo em: relatorio_YYYY-MM-DD.md`
- Arquivo `.md` criado na pasta.
- Se `CHAT_ID` ausente: warning sobre rodar bot primeiro.
- Se `CHAT_ID` presente: `Mensagem enviada para chat_id=...`.

- [ ] **Step 2: Rodar `python bot.py` e enviar `/start`**

Run em terminal separado:
```bash
cd .llm/case-02-telegram
python bot.py
```
Expected:
- Log: `Iniciando bot Telegram...` → `Bot rodando! Ctrl+C para parar.`
- No Telegram, enviar `/start` para o bot. Resposta de boas-vindas chega.
- Log: `CHAT_ID=<numero> salvo no .env`
- Verificar `.env` da raiz: linha `CHAT_ID=...` presente. Sem duplicatas.

- [ ] **Step 3: Testar `/relatorio` e mensagem livre**

No Telegram:
- `/relatorio` → bot responde "Gerando relatório..." e em seguida envia o markdown completo (split se > 4096 chars).
- Mensagem livre: "Qual o segmento com maior receita?" → resposta com número real.

- [ ] **Step 4: Confirmar sem vazamento em logs**

Inspecionar logs do terminal: confirmar que NENHUM token, senha ou URL com credencial apareceu em saída.

- [ ] **Step 5: Sanidade final — nenhuma referência a `profiles.yml` ou `os.getenv` direto**

Run:
```bash
grep -rn "profiles.yml\|os.getenv" .llm/case-02-telegram/
```
Expected: sem matches (ou apenas em comentários/docstrings, se houver).

---

## Critérios de aceite globais

1. ✅ `python agente.py` executa as 4 queries com schemas corretos do PRD e gera `relatorio_YYYY-MM-DD.md`.
2. ✅ `python bot.py` responde `/start`, `/relatorio` e mensagens livres; persiste `CHAT_ID` no `.env` da raiz.
3. ✅ `Settings()` falha rápido se variável obrigatória faltar.
4. ✅ Nenhum acesso a `~/.dbt/profiles.yml` em nenhum arquivo do case.
5. ✅ Nenhuma credencial em log ou em código fonte.
6. ✅ `ruff check` passa sem erros.
7. ✅ Após `/start` no bot, rodar `python agente.py` envia o relatório direto ao Telegram (modo cron).
