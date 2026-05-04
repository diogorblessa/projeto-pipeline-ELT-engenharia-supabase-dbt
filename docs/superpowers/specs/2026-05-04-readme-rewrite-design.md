# Design: Reescrita do README.md

**Data:** 2026-05-04  
**Abordagem escolhida:** C — Híbrido (portfólio + educacional)

---

## Objetivo

Reescrever o README.md seguindo o template definido pelo usuário, tornando a Arquitetura Medalhão visível e explicada, apresentando a estrutura de diretórios em bloco `text`, integrando screenshots dos cases e marcando o Case 02 como "Em construção".

---

## Estrutura de Seções

### 1. Título
`# Pipeline ELT de Engenharia de Dados para E-commerce`

### 2. Sobre
Descrição do projeto como pipeline ELT completo de ponta a ponta:
- Extração de Parquets do S3 → PostgreSQL via Python (boto3, pandas, SQLAlchemy)
- Transformação via dbt com Arquitetura Medalhão (Bronze → Silver → Gold)
- Consumo por aplicações analíticas: Dashboard Streamlit (Case 01) e Agente Telegram com Claude API (Case 02)
- Contexto: projeto de portfólio/aprendizado cobrindo toda a cadeia de dados

### 3. Objetivos de Aprendizado
Lista técnica:
- Construir pipeline ELT com Python (boto3, pandas, SQLAlchemy)
- Modelar dados com dbt e Arquitetura Medalhão (Bronze → Silver → Gold)
- Aplicar qualidade de dados: deduplicação, tipagem, integridade referencial
- Criar Data Marts por área de negócio (Vendas, CS, Pricing)
- Consumir dados via Streamlit (Case 01) e agente Telegram com Claude API (Case 02)
- Gerenciar ambiente com uv workspace, Docker e variáveis de ambiente seguras

### 4. Estrutura do Projeto
Bloco de código `text` com árvore de diretórios (sem `.git`, `.venv`, caches), com comentários inline por pasta. Cobre:
- `extract_load/` — extração S3 e carga PostgreSQL
- `transform/` — modelos dbt (bronze/, silver/, gold/)
- `.llm/case-01-dashboard/` — Case 01: Dashboard Streamlit
- `.llm/case-02-telegram/` — Case 02: Agente Telegram (Em construção)
- `assets/` — screenshots e diagramas
- `scripts/` — script de pipeline completo

### 5. Arquitetura Medalhão (seção central)
Diagrama ASCII expandido em bloco de código, seguido de bullets explicando cada camada:

```
[ S3 Bucket ]  →  [ Extract & Load ]  →  [ PostgreSQL: schema public ]
  (Parquets)       boto3 + pandas            (tabelas raw brutas)
                   SQLAlchemy                        │
                                    ┌────────────────┼────────────────┐
                                    ▼                ▼                ▼
                               BRONZE             SILVER            GOLD
                              (VIEWs)            (TABLEs)         (TABLEs)
                          Cópia fiel da       Dados limpos,    Dimensões, Fatos
                          fonte. Contrato     tipados e        e Marts por área
                          do dado.            deduplicados.    de negócio.
```

Bullets de explicação:
- **Bronze:** espelho exato das fontes raw, sem transformação. Serve como contrato do dado.
- **Silver:** limpeza, tipagem, deduplicação, padronização textual, integridade referencial.
- **Gold:** modelo dimensional (dim/fct) + marts finais por área (Sales, CS, Pricing).

### 6. Conteúdo — Cases

#### Case 01 — Dashboard Streamlit (completo)
- Tabela: Página | Perfil | Conteúdo
- Screenshots integradas usando imagens de `assets/dashboard/`:
  - `vendas_01.png` (página Vendas)
  - `clientes_01.png` e `clientes_02.png` (página Clientes)
  - `pricing_01.png` e `pricing_02.png` (página Pricing)

#### Case 02 — Agente Telegram + Claude API (Em construção)
- Badge/nota "🚧 Em construção"
- Descrição do que será: chat livre via tool use, relatório executivo para 3 diretores, envio automático via API HTTP
- Sem screenshots (ainda não implementado)

### 7. Tecnologias e Ferramentas
Tabela: Ferramenta | Propósito

| Ferramenta | Propósito |
|---|---|
| Python 3.11 + uv | Runtime e gerenciador de dependências (workspace) |
| boto3 + pandas | Extração de Parquets do S3 |
| SQLAlchemy + psycopg2 | Carga no PostgreSQL |
| dbt-core + dbt-postgres | Transformação e modelagem analítica |
| PostgreSQL (Supabase) | Data warehouse |
| Streamlit | Dashboard analítico (Case 01) |
| Claude API (Anthropic) | LLM para agente de dados (Case 02) |
| python-telegram-bot | Interface do agente via Telegram (Case 02) |
| Docker + docker-compose | Ambiente reproduzível |
| ruff | Lint e formatação |
| pytest | Testes unitários |

### 8. Como Usar

#### Instalação
```bash
rm -rf .venv
uv sync --all-packages
cp .env.example .env
# Preencher .env com credenciais reais (ver .env.example)
```

#### Execução — Pipeline completo
```bash
./scripts/run-pipeline.sh
```

#### Execução — Etapas avulsas
- Extract + Load
- dbt run/test
- pytest
- ruff check/format
- Docker (extract, dbt run, dbt test)

#### Dashboard (Case 01)
```bash
cd .llm/case-01-dashboard
streamlit run app.py
```

### 9. Recursos Adicionais
- `transform/PRD-dbt.md` — Spec completa dos modelos dbt
- `.llm/database.md` — Schemas das tabelas Gold
- `.llm/case-01-dashboard/PRD-dashboard.md` — Spec do Dashboard
- `.llm/case-02-telegram/PRD-agente-relatorios.md` — Spec do Agente Telegram

### 10. Autor
**Diogo Lessa**  
LinkedIn: https://www.linkedin.com/in/diogorblessa/

---

## Assets disponíveis

- `assets/dashboard/vendas_01.png`
- `assets/dashboard/clientes_01.png`
- `assets/dashboard/clientes_02.png`
- `assets/dashboard/pricing_01.png`
- `assets/dashboard/pricing_02.png`
- `assets/diagramas/` — vazio no momento

---

## Decisões

- Pasta `.llm/` incluída na árvore de diretórios pois contém os cases (parte central do projeto)
- Case 02 descrito em texto (sem screenshots), com marcação explícita de "Em construção"
- Diagrama ASCII como bloco de código simples (sem dependências externas)
- Comandos Docker mantidos em seção separada dentro de "Como Usar"
