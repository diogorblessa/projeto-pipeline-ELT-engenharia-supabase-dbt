# Refatoração — Case 02 (Agente Telegram)

**Escopo:** refatorar `.llm/case-02-telegram/agente.py` e `db.py` em 3 arquivos modulares (`agente.py`, `bot.py`, `db.py`), corrigir bugs, eliminar fontes de vazamento de credencial e alinhar com `PRD-agente-relatorios.md`, `database.md` e `CLAUDE.md`.

---

## 1. Problemas no estado atual

| # | Problema | Severidade |
|---|---|---|
| 1 | `agente.py` referencia `public_gold_sales.vendas_temporais`, `public_gold.clientes_segmentacao`, `public_gold.precos_competitividade` — mas as tabelas reais são `public_gold_sales.gold_sales_vendas_temporais`, `public_gold_cs.gold_customer_success_clientes_segmentacao`, `public_gold_pricing.gold_pricing_precos_competitividade`. | Crítico |
| 2 | `db.py` cai em `~/.dbt/profiles.yml` se `POSTGRES_URL` ausente — lê senha em texto plano de YAML. | Crítico |
| 3 | `salvar_chat_id` só atualiza `os.environ` em memória; não persiste no `.env` como o PRD descreve. | Médio |
| 4 | `MODEL = "claude-sonnet-4-6"` hardcoded em `agente.py`. | Médio |
| 5 | `.env` carregado de `.llm/case-02-telegram/.env`; já existe `.env` na raiz com `POSTGRES_URL` reaproveitável. | Médio |
| 6 | `agente.py` mistura 5 responsabilidades (Settings/schema/chat/relatório/bot) em ~340 linhas. | Estrutural |
| 7 | `bot.py` separado não existe (PRD prevê dois entry points: `agente.py` standalone e `bot.py` polling). | Estrutural |

---

## 2. Decisões de design

| Tópico | Decisão | Motivo |
|---|---|---|
| Estrutura | 3 arquivos: `db.py`, `agente.py`, `bot.py` (PRD literal). Sem `config.py`, sem `src/`. | `Settings` cabe no topo de `agente.py`; `bot.py` já importa daí. Adicionar 4º arquivo seria gordura. |
| Validação de Settings | `pydantic-settings` + `SecretStr`. | Falha rápida na inicialização; mascara segredos no `repr`; já é o padrão em `extract_load`. |
| Localização do `.env` | `.env` da raiz do projeto (compartilhado com `extract_load`/`case-01-dashboard`). | Reduz superfície de exposição; elimina divergência entre `.env`s. |
| Fallback `profiles.yml` | Removido. | Texto plano em YAML é vetor de vazamento. Sem `POSTGRES_URL` ⇒ falha clara. |
| `ANTHROPIC_MODEL` | Constante em `Settings` com default `claude-sonnet-4-6`, configurável via env var. | Modelo muda raramente; default no código + override por env var resolve sem fricção. |
| `CHAT_ID` persistente | Escrito no `.env` da raiz por `salvar_chat_id` (regex update-or-append). | Comportamento literal do PRD. Cron com `agente.py` standalone passa a funcionar após primeira interação no bot. |
| Bug de schema | Corrigir para nomes do PRD em `SCHEMA` e `QUERIES_RELATORIO`. | Três fontes de verdade independentes (PRD, `database.md`, `CLAUDE.md`) confirmam. |

---

## 3. Estrutura final

```
.llm/case-02-telegram/
├── db.py              ~30 linhas   engine + execute_query (SELECT/WITH only)
├── agente.py          ~190 linhas  Settings + SCHEMA + chat + gerar_relatorio + enviar_telegram + main
├── bot.py             ~80 linhas   handlers + salvar_chat_id + polling
└── requirements.txt   dependências do case
```

`Settings` vive em `agente.py`. `bot.py` faz `from agente import Settings, chat, gerar_relatorio, enviar_telegram`.

---

## 4. Conteúdo de cada arquivo

### 4.1 `agente.py`

```
# ── Settings (pydantic-settings) ─────────────────────────────────────
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"   # raiz do projeto

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

# ── Constantes ───────────────────────────────────────────────────────
SCHEMA = """3 tabelas com nomes corretos do PRD"""
TOOL = {"name": "executar_sql", ...}
MAX_ITERACOES_TOOL = 10
TELEGRAM_MAX_CHARS = 4096
QUERIES_RELATORIO = {                # 4 queries do PRD com schemas corretos
    "vendas":   "SELECT ... FROM public_gold_sales.gold_sales_vendas_temporais ...",
    "clientes": "SELECT ... FROM public_gold_cs.gold_customer_success_clientes_segmentacao ...",
    "pricing":  "SELECT ... FROM public_gold_pricing.gold_pricing_precos_competitividade ...",
    "criticos": "SELECT ... WHERE classificacao_preco = 'MAIS_CARO_QUE_TODOS' ...",
}

# ── Funções públicas ─────────────────────────────────────────────────
def chat(pergunta: str, settings: Settings) -> str
def gerar_relatorio(settings: Settings) -> str
def enviar_telegram(texto: str, settings: Settings, chat_id: str | None = None) -> None

# ── Helpers privados ─────────────────────────────────────────────────
def _split_telegram(texto: str) -> list[str]
def _enviar_parte(token: str, chat_id: str, parte: str) -> None
def _executar_tool_call(block, settings: Settings) -> dict

# ── Main standalone ──────────────────────────────────────────────────
if __name__ == "__main__":
    settings = Settings()
    relatorio = gerar_relatorio(settings)
    if settings.chat_id:
        enviar_telegram(relatorio, settings)
    else:
        log.warning("CHAT_ID não configurado — rode bot.py e envie /start primeiro")
```

### 4.2 `db.py`

```python
def get_engine(postgres_url: SecretStr) -> Engine:
    return create_engine(postgres_url.get_secret_value())

def execute_query(sql: str, settings: Settings) -> pd.DataFrame:
    sql_clean = sql.strip().upper()
    if not (sql_clean.startswith("SELECT") or sql_clean.startswith("WITH")):
        raise ValueError("Apenas SELECT/WITH são permitidos.")
    engine = get_engine(settings.postgres_url)
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)
```

Sem fallback `profiles.yml`. Recebe `Settings` por parâmetro.

### 4.3 `bot.py`

```python
from agente import Settings, chat, gerar_relatorio, enviar_telegram

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"   # raiz

def salvar_chat_id(chat_id: int, env_path: Path = ENV_PATH) -> None:
    """Lê linhas do .env, substitui linha CHAT_ID=... ou anexa nova. UTF-8."""

async def handler_start(update, context)
async def handler_relatorio(update, context)
async def handler_mensagem(update, context)
async def _enviar_longo(update, texto)

if __name__ == "__main__":
    settings = Settings()
    app = ApplicationBuilder().token(settings.telegram.get_secret_value()).build()
    app.add_handler(CommandHandler("start", handler_start))
    app.add_handler(CommandHandler("relatorio", handler_relatorio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler_mensagem))
    app.run_polling()
```

---

## 5. Princípios de segurança

1. **`Settings()` falha rápido** se `TELEGRAM`, `ANTHROPIC_API_KEY` ou `POSTGRES_URL` faltam — antes de qualquer chamada externa.
2. **`SecretStr` em todas as credenciais.** Acesso via `.get_secret_value()` apenas no momento do uso (criação do engine, header HTTP do Telegram, init do cliente Anthropic).
3. **`db.py` recebe `Settings` por parâmetro** — não importa env vars. Testável e auditável.
4. **`bot.py` é o único módulo que escreve no `.env`** (`salvar_chat_id`). `agente.py` standalone só lê.
5. **Sem fallback YAML.** Sem hardcode de credenciais. Sem `os.getenv` espalhado.
6. **Logs nunca emitem `Settings` ou conteúdo de `SecretStr`.** O `__repr__` mascara, mas evitamos por princípio.

---

## 6. Tratamento de erros

| Cenário | Onde | Comportamento |
|---|---|---|
| `.env` incompleto | `Settings()` | `pydantic.ValidationError` — para o processo |
| Banco fora | `execute_query` | Em `chat()` vira `tool_result` de erro; em `gerar_relatorio()` aborta com log |
| API Claude indisponível | `gerar_relatorio()` | Fallback: cabeçalho de erro + 4 tabelas markdown brutas |
| SQL não-SELECT | `execute_query` | `ValueError` → `tool_result` de erro |
| Loop tool use | `chat()` | Limite `MAX_ITERACOES_TOOL = 10` |
| Mensagem > 4096 chars | `enviar_telegram` | Split; tenta `parse_mode=Markdown`, fallback texto puro |
| `CHAT_ID` ausente standalone | `__main__` de `agente.py` | Log de aviso; `.md` ainda salvo |
| Erro escrevendo `.env` | `salvar_chat_id` | Log de erro, bot continua (não-fatal) |

---

## 7. Logging

`logging.basicConfig` único no topo de `agente.py`:

```python
logging.basicConfig(
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
```

`bot.py` reusa via `logging.getLogger(__name__)`. Mensagens em pt-BR como no PRD ("Consultando vendas...", "Enviando para Claude API...", "CHAT_ID=xxx salvo no .env").

---

## 8. Dependências

`.llm/case-02-telegram/requirements.txt`:

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

Removidos: `python-dotenv` (substituído por `pydantic-settings`), `pyyaml` (sem fallback `profiles.yml`).

---

## 9. Variáveis de ambiente (raiz `.env`)

Adicionadas ao `.env.example` da raiz (já feito):

```
TELEGRAM=CHANGE_ME
ANTHROPIC_API_KEY=sk-ant-CHANGE_ME
ANTHROPIC_MODEL=claude-sonnet-4-6
CHAT_ID=
```

`POSTGRES_URL` já existe no `.env` da raiz e é reaproveitada.

---

## 10. `.gitignore`

Verificar se cobre `.llm/case-02-telegram/relatorio_*.md`. Caso contrário, adicionar à raiz. `.env` da raiz já está ignorado.

---

## 11. Como rodar (após refatoração)

**Modo interativo (bot)**
```bash
cd .llm/case-02-telegram
pip install -r requirements.txt
python bot.py
```
No Telegram: `/start` → `CHAT_ID` salvo automaticamente no `.env` da raiz.

**Modo standalone (cron / manual)**
```bash
cd .llm/case-02-telegram
python agente.py
```
Gera relatório, salva `relatorio_YYYY-MM-DD.md`, envia para `CHAT_ID` se configurado.

---

## 12. Critérios de sucesso

1. `python -c "from agente import Settings; Settings()"` carrega sem erro com `.env` preenchido; falha clara se faltar variável obrigatória.
2. `python agente.py` executa as 4 queries com nomes de schema corretos, gera `.md` e (se `CHAT_ID` presente) envia ao Telegram.
3. `python bot.py` responde `/start`, persiste `CHAT_ID` no `.env` da raiz e atende `/relatorio` e mensagens livres.
4. Nenhuma credencial aparece em log ou em código fonte.
5. Sem leitura de `~/.dbt/profiles.yml` em qualquer arquivo do case.
