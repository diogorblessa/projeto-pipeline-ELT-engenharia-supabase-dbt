# DBT Gold Dimensional Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reestruturar a camada Gold do dbt para uma modelagem estrela com modelos `gold_dim_*`, `gold_fct_*` e marts finais `gold_*`, atualizando testes e referencias documentais.

**Architecture:** Bronze e Silver permanecem como estao. A Gold passa a ter `gold/dimensional/` com dimensoes/fatos reutilizaveis e `gold/marts/<setor>/` com os tres data marts finais para consumo dos cases 01 e 02. Chaves e relacionamentos serao validados por testes dbt em `transform/models/gold/_gold_models.yml`, sem constraints fisicas no PostgreSQL.

**Tech Stack:** dbt-core + dbt-postgres, PostgreSQL/Supabase, SQL PostgreSQL, YAML schema tests, PowerShell/Git Bash para comandos locais.

---

## File Structure

### Create

- `transform/models/gold/dimensional/gold_dim_clientes.sql`: dimensao de clientes baseada em `silver_clientes`.
- `transform/models/gold/dimensional/gold_dim_produtos.sql`: dimensao de produtos baseada em `silver_produtos`.
- `transform/models/gold/dimensional/gold_dim_datas.sql`: dimensao de datas unindo datas de vendas e coletas de preco.
- `transform/models/gold/dimensional/gold_dim_concorrentes.sql`: dimensao de concorrentes com `concorrente_key` deterministica.
- `transform/models/gold/dimensional/gold_fct_vendas.sql`: fato principal de vendas, uma linha por `id_venda`.
- `transform/models/gold/dimensional/gold_fct_precos_competidores.sql`: fato auxiliar de pricing, uma linha por `id_produto + concorrente_key + data_da_coleta`.
- `transform/models/gold/marts/sales/gold_sales_vendas_temporais.sql`: mart final de vendas temporais.
- `transform/models/gold/marts/customer_success/gold_customer_success_clientes_segmentacao.sql`: mart final de customer success.
- `transform/models/gold/marts/pricing/gold_pricing_precos_competitividade.sql`: mart final de pricing.
- `transform/models/gold/_gold_models.yml`: documentacao e testes dbt da camada Gold.

### Modify

- `transform/dbt_project.yml`: mapear `gold/dimensional` para `public_gold` e `gold/marts/*` para os schemas setoriais.
- `README.md`: atualizar nomes e caminhos dos marts Gold.
- `CLAUDE.md`: atualizar arquitetura, comandos/referencias e lista de modelos Gold.
- `transform/PRD-dbt.md`: atualizar a especificacao dbt para a nova Gold dimensional.
- `.llm/database.md`: atualizar schemas, tabelas, exemplos SQL e diagrama textual.
- `.llm/case-01-dashboard/feature.md`: trocar referencias antigas pelos novos marts.
- `.llm/case-01-dashboard/PRD-dashboard.md`: trocar referencias antigas pelos novos marts.
- `.llm/case-02-telegram/PRD-agente-relatorios.md`: trocar referencias antigas pelos novos marts.
- `docs/superpowers/specs/2026-04-28-reorganizacao-elt-design.md`: atualizar snapshot arquitetural que cita os nomes Gold antigos.
- `docs/superpowers/plans/2026-04-28-reorganizacao-elt.md`: atualizar snapshot/plano historico que cita os nomes Gold antigos.

### Delete

- `transform/models/gold/sales/vendas_temporais.sql`
- `transform/models/gold/customer_success/clientes_segmentacao.sql`
- `transform/models/gold/pricing/precos_competitividade.sql`

Use `git mv` para preservar historico nos tres marts finais.

---

## Task 1: Update dbt Gold directory configuration

**Files:**
- Modify: `transform/dbt_project.yml`

- [ ] **Step 1: Edit `dbt_project.yml` Gold config**

Replace the current `gold:` block with:

```yaml
    gold:
      +materialized: table            # Tables - modelos analiticos prontos para consumo
      +tags: ["gold"]
      +meta:
        modeling_layer: gold

      dimensional:
        +schema: gold                 # Schema: public_gold
        +tags: ["gold", "dimensional"]
        +meta:
          gold_role: dimensional

      marts:
        +tags: ["gold", "mart", "kpi", "metrics"]
        +meta:
          gold_role: mart
        sales:
          +schema: gold_sales         # Schema: public_gold_sales
        customer_success:
          +schema: gold_cs            # Schema: public_gold_cs
        pricing:
          +schema: gold_pricing       # Schema: public_gold_pricing
```

- [ ] **Step 2: Parse dbt config**

Run:

```bash
uv run --package transform dbt parse --project-dir transform --profiles-dir transform
```

Expected:

```text
Completed successfully
```

If `dbt parse` fails because the new directories do not exist yet, create the directories before re-running:

```powershell
New-Item -ItemType Directory -Force -Path .\transform\models\gold\dimensional
New-Item -ItemType Directory -Force -Path .\transform\models\gold\marts\sales
New-Item -ItemType Directory -Force -Path .\transform\models\gold\marts\customer_success
New-Item -ItemType Directory -Force -Path .\transform\models\gold\marts\pricing
```

- [ ] **Step 3: Commit dbt config change**

Run:

```bash
git add transform/dbt_project.yml
git commit -m "chore(dbt): configure gold dimensional hierarchy"
```

---

## Task 2: Create Gold dimension models

**Files:**
- Create: `transform/models/gold/dimensional/gold_dim_clientes.sql`
- Create: `transform/models/gold/dimensional/gold_dim_produtos.sql`
- Create: `transform/models/gold/dimensional/gold_dim_datas.sql`
- Create: `transform/models/gold/dimensional/gold_dim_concorrentes.sql`

- [ ] **Step 1: Create `gold_dim_clientes.sql`**

Content:

```sql
SELECT
    c.id_cliente,
    c.nome_cliente,
    c.estado,
    c.pais,
    c.data_cadastro
FROM {{ ref('silver_clientes') }} c
```

- [ ] **Step 2: Create `gold_dim_produtos.sql`**

Content:

```sql
SELECT
    p.id_produto,
    p.nome_produto,
    p.categoria,
    p.marca,
    p.preco_atual,
    p.faixa_preco,
    p.data_criacao
FROM {{ ref('silver_produtos') }} p
```

- [ ] **Step 3: Create `gold_dim_datas.sql`**

Content:

```sql
WITH datas_unificadas AS (
    SELECT
        v.data_da_venda AS data
    FROM {{ ref('silver_vendas') }} v

    UNION

    SELECT
        pc.data_da_coleta AS data
    FROM {{ ref('silver_preco_competidores') }} pc
),

datas_validas AS (
    SELECT DISTINCT
        data
    FROM datas_unificadas
    WHERE data IS NOT NULL
)

SELECT
    data,
    EXTRACT(YEAR FROM data::timestamp) AS ano,
    EXTRACT(MONTH FROM data::timestamp) AS mes,
    EXTRACT(DAY FROM data::timestamp) AS dia,
    EXTRACT(DOW FROM data::timestamp) AS dia_semana,
    CASE EXTRACT(DOW FROM data::timestamp)
        WHEN 0 THEN 'Domingo'
        WHEN 1 THEN 'Segunda'
        WHEN 2 THEN 'Terca'
        WHEN 3 THEN 'Quarta'
        WHEN 4 THEN 'Quinta'
        WHEN 5 THEN 'Sexta'
        WHEN 6 THEN 'Sabado'
    END AS dia_semana_nome
FROM datas_validas
ORDER BY data
```

- [ ] **Step 4: Create `gold_dim_concorrentes.sql`**

Content:

```sql
SELECT DISTINCT
    md5(lower(trim(pc.nome_concorrente))) AS concorrente_key,
    pc.nome_concorrente
FROM {{ ref('silver_preco_competidores') }} pc
WHERE pc.nome_concorrente IS NOT NULL
```

- [ ] **Step 5: Parse dimension models**

Run:

```bash
uv run --package transform dbt parse --project-dir transform --profiles-dir transform
```

Expected:

```text
Completed successfully
```

- [ ] **Step 6: Run only dimension models**

Run:

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s gold_dim_clientes gold_dim_produtos gold_dim_datas gold_dim_concorrentes
```

Expected:

```text
4 of 4 OK
Completed successfully
```

- [ ] **Step 7: Commit dimensions**

Run:

```bash
git add transform/models/gold/dimensional/gold_dim_clientes.sql transform/models/gold/dimensional/gold_dim_produtos.sql transform/models/gold/dimensional/gold_dim_datas.sql transform/models/gold/dimensional/gold_dim_concorrentes.sql
git commit -m "feat(dbt): add gold dimension models"
```

---

## Task 3: Create Gold fact models

**Files:**
- Create: `transform/models/gold/dimensional/gold_fct_vendas.sql`
- Create: `transform/models/gold/dimensional/gold_fct_precos_competidores.sql`

- [ ] **Step 1: Create `gold_fct_vendas.sql`**

Content:

```sql
SELECT
    v.id_venda,
    v.id_cliente,
    v.id_produto,
    v.data_da_venda AS data_venda,
    v.canal_venda,
    v.quantidade,
    v.preco_unitario,
    v.receita_total,
    v.hora_venda
FROM {{ ref('silver_vendas') }} v
```

- [ ] **Step 2: Create `gold_fct_precos_competidores.sql`**

Content:

```sql
WITH precos AS (
    SELECT
        pc.id_produto,
        md5(lower(trim(pc.nome_concorrente))) AS concorrente_key,
        pc.data_da_coleta,
        pc.preco_concorrente
    FROM {{ ref('silver_preco_competidores') }} pc
    WHERE pc.nome_concorrente IS NOT NULL
)

SELECT
    md5(
        id_produto::text
        || '|'
        || concorrente_key
        || '|'
        || data_da_coleta::text
    ) AS preco_competidor_key,
    id_produto,
    concorrente_key,
    data_da_coleta,
    preco_concorrente
FROM precos
```

- [ ] **Step 3: Parse fact models**

Run:

```bash
uv run --package transform dbt parse --project-dir transform --profiles-dir transform
```

Expected:

```text
Completed successfully
```

- [ ] **Step 4: Run only fact models with parents**

Run:

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s +gold_fct_vendas +gold_fct_precos_competidores
```

Expected:

```text
Completed successfully
```

- [ ] **Step 5: Commit facts**

Run:

```bash
git add transform/models/gold/dimensional/gold_fct_vendas.sql transform/models/gold/dimensional/gold_fct_precos_competidores.sql
git commit -m "feat(dbt): add gold fact models"
```

---

## Task 4: Move and rewrite final Gold marts

**Files:**
- Move: `transform/models/gold/sales/vendas_temporais.sql` -> `transform/models/gold/marts/sales/gold_sales_vendas_temporais.sql`
- Move: `transform/models/gold/customer_success/clientes_segmentacao.sql` -> `transform/models/gold/marts/customer_success/gold_customer_success_clientes_segmentacao.sql`
- Move: `transform/models/gold/pricing/precos_competitividade.sql` -> `transform/models/gold/marts/pricing/gold_pricing_precos_competitividade.sql`

- [ ] **Step 1: Move the mart files with `git mv`**

Run:

```bash
git mv transform/models/gold/sales/vendas_temporais.sql transform/models/gold/marts/sales/gold_sales_vendas_temporais.sql
git mv transform/models/gold/customer_success/clientes_segmentacao.sql transform/models/gold/marts/customer_success/gold_customer_success_clientes_segmentacao.sql
git mv transform/models/gold/pricing/precos_competitividade.sql transform/models/gold/marts/pricing/gold_pricing_precos_competitividade.sql
```

- [ ] **Step 2: Rewrite `gold_sales_vendas_temporais.sql`**

Content:

```sql
SELECT
    f.data_venda,
    d.ano AS ano_venda,
    d.mes AS mes_venda,
    d.dia AS dia_venda,
    d.dia_semana_nome AS dia_da_semana,
    f.hora_venda,
    SUM(f.receita_total) AS receita_total,
    SUM(f.quantidade) AS quantidade_total,
    COUNT(DISTINCT f.id_venda) AS total_vendas,
    COUNT(DISTINCT f.id_cliente) AS total_clientes_unicos,
    AVG(f.receita_total) AS ticket_medio
FROM {{ ref('gold_fct_vendas') }} f
LEFT JOIN {{ ref('gold_dim_datas') }} d
    ON f.data_venda = d.data
GROUP BY 1, 2, 3, 4, 5, 6
ORDER BY data_venda DESC, f.hora_venda
```

- [ ] **Step 3: Rewrite `gold_customer_success_clientes_segmentacao.sql`**

Content:

```sql
WITH receita_por_cliente AS (
    SELECT
        f.id_cliente,
        c.nome_cliente,
        c.estado,
        SUM(f.receita_total) AS receita_total,
        COUNT(DISTINCT f.id_venda) AS total_compras,
        AVG(f.receita_total) AS ticket_medio,
        MIN(f.data_venda) AS primeira_compra,
        MAX(f.data_venda) AS ultima_compra
    FROM {{ ref('gold_fct_vendas') }} f
    LEFT JOIN {{ ref('gold_dim_clientes') }} c
        ON f.id_cliente = c.id_cliente
    GROUP BY f.id_cliente, c.nome_cliente, c.estado
)

SELECT
    id_cliente AS cliente_id,
    nome_cliente,
    estado,
    receita_total,
    total_compras,
    ticket_medio,
    primeira_compra,
    ultima_compra,
    CASE
        WHEN receita_total >= {{ var('segmentacao_vip_threshold', 10000) }} THEN 'VIP'
        WHEN receita_total >= {{ var('segmentacao_top_tier_threshold', 5000) }} THEN 'TOP_TIER'
        ELSE 'REGULAR'
    END AS segmento_cliente,
    ROW_NUMBER() OVER (ORDER BY receita_total DESC) AS ranking_receita
FROM receita_por_cliente
ORDER BY receita_total DESC
```

- [ ] **Step 4: Rewrite `gold_pricing_precos_competitividade.sql`**

Content:

```sql
WITH precos_por_produto AS (
    SELECT
        p.id_produto,
        p.nome_produto,
        p.categoria,
        p.marca,
        p.preco_atual AS nosso_preco,
        AVG(fp.preco_concorrente) AS preco_medio_concorrentes,
        MIN(fp.preco_concorrente) AS preco_minimo_concorrentes,
        MAX(fp.preco_concorrente) AS preco_maximo_concorrentes,
        COUNT(DISTINCT fp.concorrente_key) AS total_concorrentes
    FROM {{ ref('gold_dim_produtos') }} p
    LEFT JOIN {{ ref('gold_fct_precos_competidores') }} fp
        ON p.id_produto = fp.id_produto
    LEFT JOIN {{ ref('gold_dim_concorrentes') }} c
        ON fp.concorrente_key = c.concorrente_key
    GROUP BY p.id_produto, p.nome_produto, p.categoria, p.marca, p.preco_atual
),

vendas_por_produto AS (
    SELECT
        f.id_produto,
        SUM(f.receita_total) AS receita_total,
        SUM(f.quantidade) AS quantidade_total
    FROM {{ ref('gold_fct_vendas') }} f
    GROUP BY f.id_produto
)

SELECT
    pp.id_produto AS produto_id,
    pp.nome_produto,
    pp.categoria,
    pp.marca,
    pp.nosso_preco,
    pp.preco_medio_concorrentes,
    pp.preco_minimo_concorrentes,
    pp.preco_maximo_concorrentes,
    pp.total_concorrentes,
    CASE
        WHEN pp.preco_medio_concorrentes = 0 THEN NULL
        ELSE ((pp.nosso_preco - pp.preco_medio_concorrentes) / pp.preco_medio_concorrentes) * 100
    END AS diferenca_percentual_vs_media,
    CASE
        WHEN pp.preco_minimo_concorrentes = 0 THEN NULL
        ELSE ((pp.nosso_preco - pp.preco_minimo_concorrentes) / pp.preco_minimo_concorrentes) * 100
    END AS diferenca_percentual_vs_minimo,
    CASE
        WHEN pp.nosso_preco > pp.preco_maximo_concorrentes THEN 'MAIS_CARO_QUE_TODOS'
        WHEN pp.nosso_preco < pp.preco_minimo_concorrentes THEN 'MAIS_BARATO_QUE_TODOS'
        WHEN pp.nosso_preco > pp.preco_medio_concorrentes THEN 'ACIMA_DA_MEDIA'
        WHEN pp.nosso_preco < pp.preco_medio_concorrentes THEN 'ABAIXO_DA_MEDIA'
        ELSE 'NA_MEDIA'
    END AS classificacao_preco,
    COALESCE(vp.receita_total, 0) AS receita_total,
    COALESCE(vp.quantidade_total, 0) AS quantidade_total
FROM precos_por_produto pp
LEFT JOIN vendas_por_produto vp
    ON pp.id_produto = vp.id_produto
WHERE pp.preco_medio_concorrentes IS NOT NULL
ORDER BY diferenca_percentual_vs_media DESC
```

- [ ] **Step 5: Run only Gold marts with parents**

Run:

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform -s +gold_sales_vendas_temporais +gold_customer_success_clientes_segmentacao +gold_pricing_precos_competitividade
```

Expected:

```text
Completed successfully
```

- [ ] **Step 6: Confirm old mart files are gone**

Run:

```bash
Test-Path .\transform\models\gold\sales\vendas_temporais.sql
Test-Path .\transform\models\gold\customer_success\clientes_segmentacao.sql
Test-Path .\transform\models\gold\pricing\precos_competitividade.sql
```

Expected:

```text
False
False
False
```

- [ ] **Step 7: Commit mart rename and rewrites**

Run:

```bash
git add transform/models/gold
git commit -m "feat(dbt): rename gold marts and use dimensional base"
```

---

## Task 5: Add Gold schema tests and documentation

**Files:**
- Create: `transform/models/gold/_gold_models.yml`

- [ ] **Step 1: Create `_gold_models.yml`**

Content:

```yaml
version: 2

models:
  - name: gold_dim_clientes
    description: "Dimensao de clientes para a camada Gold."
    columns:
      - name: id_cliente
        description: "Chave unica do cliente."
        tests:
          - unique
          - not_null

  - name: gold_dim_produtos
    description: "Dimensao de produtos para a camada Gold."
    columns:
      - name: id_produto
        description: "Chave unica do produto."
        tests:
          - unique
          - not_null

  - name: gold_dim_datas
    description: "Dimensao de datas unificada para vendas e coletas de preco."
    columns:
      - name: data
        description: "Data calendario usada pelas fatos."
        tests:
          - unique
          - not_null

  - name: gold_dim_concorrentes
    description: "Dimensao de concorrentes para analises de pricing."
    columns:
      - name: concorrente_key
        description: "Chave tecnica deterministica do concorrente."
        tests:
          - unique
          - not_null
      - name: nome_concorrente
        description: "Nome original do concorrente."
        tests:
          - not_null

  - name: gold_fct_vendas
    description: "Fato principal de vendas, com uma linha por venda."
    columns:
      - name: id_venda
        description: "Chave unica da venda."
        tests:
          - unique
          - not_null
      - name: id_cliente
        description: "Chave estrangeira logica para gold_dim_clientes."
        tests:
          - not_null
          - relationships:
              to: ref('gold_dim_clientes')
              field: id_cliente
      - name: id_produto
        description: "Chave estrangeira logica para gold_dim_produtos."
        tests:
          - not_null
          - relationships:
              to: ref('gold_dim_produtos')
              field: id_produto
      - name: data_venda
        description: "Data da venda relacionada a gold_dim_datas."
        tests:
          - not_null
          - relationships:
              to: ref('gold_dim_datas')
              field: data

  - name: gold_fct_precos_competidores
    description: "Fato auxiliar de precos de concorrentes por produto, concorrente e data."
    columns:
      - name: preco_competidor_key
        description: "Chave tecnica unica da medicao de preco."
        tests:
          - unique
          - not_null
      - name: id_produto
        description: "Chave estrangeira logica para gold_dim_produtos."
        tests:
          - not_null
          - relationships:
              to: ref('gold_dim_produtos')
              field: id_produto
      - name: concorrente_key
        description: "Chave estrangeira logica para gold_dim_concorrentes."
        tests:
          - not_null
          - relationships:
              to: ref('gold_dim_concorrentes')
              field: concorrente_key
      - name: data_da_coleta
        description: "Data da coleta relacionada a gold_dim_datas."
        tests:
          - not_null
          - relationships:
              to: ref('gold_dim_datas')
              field: data

  - name: gold_sales_vendas_temporais
    description: "Data mart Gold de vendas temporais para a area comercial."
    columns:
      - name: data_venda
        description: "Data agregada da venda."
        tests:
          - not_null

  - name: gold_customer_success_clientes_segmentacao
    description: "Data mart Gold de segmentacao de clientes para Customer Success."
    columns:
      - name: cliente_id
        description: "Identificador unico do cliente no mart."
        tests:
          - unique
          - not_null

  - name: gold_pricing_precos_competitividade
    description: "Data mart Gold de competitividade de precos para Pricing."
    columns:
      - name: produto_id
        description: "Identificador unico do produto no mart."
        tests:
          - unique
          - not_null
```

- [ ] **Step 2: Parse schema tests**

Run:

```bash
uv run --package transform dbt parse --project-dir transform --profiles-dir transform
```

Expected:

```text
Completed successfully
```

- [ ] **Step 3: Run Gold tests**

Run:

```bash
uv run --package transform dbt test --project-dir transform --profiles-dir transform -s tag:gold
```

Expected:

```text
Completed successfully
```

If a relationship test fails because existing source data has an orphan key, stop and report the exact failing test. Do not silently filter the facts to hide the orphan.

- [ ] **Step 4: Commit Gold tests**

Run:

```bash
git add transform/models/gold/_gold_models.yml
git commit -m "test(dbt): add gold dimensional contracts"
```

---

## Task 6: Update dbt PRD and root project docs

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `transform/PRD-dbt.md`

- [ ] **Step 1: Update `README.md` Gold references**

Replace mentions of:

```text
Bronze -> Silver -> Gold
```

with wording that keeps the medalhao flow and adds the dimensional split:

```text
Bronze -> Silver -> Gold dimensional -> Gold marts
```

Ensure the documentation names the final marts:

```text
public_gold_sales.gold_sales_vendas_temporais
public_gold_cs.gold_customer_success_clientes_segmentacao
public_gold_pricing.gold_pricing_precos_competitividade
```

- [ ] **Step 2: Update `CLAUDE.md` architecture section**

Replace the current Gold listing:

```text
public_gold_sales.vendas_temporais          -> Analytics de vendas
public_gold_cs.clientes_segmentacao         -> Segmentacao de clientes
public_gold_pricing.precos_competitividade  -> Inteligencia de precos
```

with:

```text
public_gold.gold_dim_clientes
public_gold.gold_dim_produtos
public_gold.gold_dim_datas
public_gold.gold_dim_concorrentes
public_gold.gold_fct_vendas
public_gold.gold_fct_precos_competidores
public_gold_sales.gold_sales_vendas_temporais
public_gold_cs.gold_customer_success_clientes_segmentacao
public_gold_pricing.gold_pricing_precos_competitividade
```

Also update the dbt structure bullet from:

```text
transform/models/gold/sales/, gold/customer_success/, gold/pricing/
```

to:

```text
transform/models/gold/dimensional/ e transform/models/gold/marts/<setor>/
```

- [ ] **Step 3: Rewrite the Gold section in `transform/PRD-dbt.md`**

Replace the old "1 modelo por data mart" statement with:

```text
Camada Gold:
- `gold/dimensional/`: dimensoes e fatos reutilizaveis em estrela.
- `gold/marts/`: data marts finais por area, consumidos por dashboard/agente.
```

Document the nine Gold models:

```text
gold_dim_clientes
gold_dim_produtos
gold_dim_datas
gold_dim_concorrentes
gold_fct_vendas
gold_fct_precos_competidores
gold_sales_vendas_temporais
gold_customer_success_clientes_segmentacao
gold_pricing_precos_competitividade
```

- [ ] **Step 4: Search for old Gold names in the three files**

Run:

```bash
rg -n "public_gold_sales\\.vendas_temporais|public_gold_cs\\.clientes_segmentacao|public_gold_pricing\\.precos_competitividade|models/gold/sales|models/gold/customer_success|models/gold/pricing" README.md CLAUDE.md transform/PRD-dbt.md
```

Expected: no matches.

- [ ] **Step 5: Commit root/dbt docs**

Run:

```bash
git add README.md CLAUDE.md transform/PRD-dbt.md
git commit -m "docs(dbt): update gold dimensional documentation"
```

---

## Task 7: Update `.llm` references for cases 01 and 02

**Files:**
- Modify: `.llm/database.md`
- Modify: `.llm/case-01-dashboard/feature.md`
- Modify: `.llm/case-01-dashboard/PRD-dashboard.md`
- Modify: `.llm/case-02-telegram/PRD-agente-relatorios.md`

- [ ] **Step 1: Replace final mart table names**

Apply these replacements in all `.llm` files:

```text
public_gold_sales.vendas_temporais -> public_gold_sales.gold_sales_vendas_temporais
public_gold_cs.clientes_segmentacao -> public_gold_cs.gold_customer_success_clientes_segmentacao
public_gold_pricing.precos_competitividade -> public_gold_pricing.gold_pricing_precos_competitividade
```

- [ ] **Step 2: Update `.llm/database.md` schema summary**

Add the dimensional base to the architecture summary:

```text
public_gold.gold_dim_clientes
public_gold.gold_dim_produtos
public_gold.gold_dim_datas
public_gold.gold_dim_concorrentes
public_gold.gold_fct_vendas
public_gold.gold_fct_precos_competidores
```

Keep the consumer guidance explicit:

```text
Dashboards e agentes devem consumir preferencialmente os marts finais em public_gold_sales, public_gold_cs e public_gold_pricing.
```

- [ ] **Step 3: Update SQL examples**

Every SQL example that reads a final mart should use the new table name. Example:

```sql
SELECT *
FROM public_gold_sales.gold_sales_vendas_temporais;
```

Do the same for Customer Success and Pricing:

```sql
SELECT *
FROM public_gold_cs.gold_customer_success_clientes_segmentacao;

SELECT *
FROM public_gold_pricing.gold_pricing_precos_competitividade;
```

- [ ] **Step 4: Search `.llm` for old names**

Run:

```bash
rg -n "public_gold_sales\\.vendas_temporais|public_gold_cs\\.clientes_segmentacao|public_gold_pricing\\.precos_competitividade|\\bvendas_temporais\\b|\\bclientes_segmentacao\\b|\\bprecos_competitividade\\b" .llm
```

Expected: no old bare mart names remain except where explicitly listed as historical names in this implementation plan. If any remain in `.llm`, update them to the new `gold_*` names.

- [ ] **Step 5: Commit `.llm` updates**

Run:

```bash
git add .llm/database.md .llm/case-01-dashboard/feature.md .llm/case-01-dashboard/PRD-dashboard.md .llm/case-02-telegram/PRD-agente-relatorios.md
git commit -m "docs(llm): align case references with gold marts"
```

---

## Task 8: Update superpowers historical docs

**Files:**
- Modify: `docs/superpowers/specs/2026-04-28-reorganizacao-elt-design.md`
- Modify: `docs/superpowers/plans/2026-04-28-reorganizacao-elt.md`

- [ ] **Step 1: Replace old final mart names in superpowers docs**

Apply:

```text
public_gold_sales.vendas_temporais -> public_gold_sales.gold_sales_vendas_temporais
public_gold_cs.clientes_segmentacao -> public_gold_cs.gold_customer_success_clientes_segmentacao
public_gold_pricing.precos_competitividade -> public_gold_pricing.gold_pricing_precos_competitividade
```

- [ ] **Step 2: Add a short note that Gold was later refined**

Where these docs describe the dbt model layout, add:

```text
Nota posterior: a camada Gold foi refinada para `gold/dimensional/` e `gold/marts/<setor>/`, mantendo os marts finais com prefixo `gold_*`.
```

- [ ] **Step 3: Search superpowers docs for stale Gold names**

Run:

```bash
rg -n "public_gold_sales\\.vendas_temporais|public_gold_cs\\.clientes_segmentacao|public_gold_pricing\\.precos_competitividade|models/gold/sales|gold/customer_success|gold/pricing" docs/superpowers
```

Expected: no stale references outside this plan's explicit replacement instructions.

- [ ] **Step 4: Commit superpowers docs**

Run:

```bash
git add -f docs/superpowers/specs/2026-04-28-reorganizacao-elt-design.md docs/superpowers/plans/2026-04-28-reorganizacao-elt.md
git commit -m "docs: align prior plans with gold dimensional naming"
```

---

## Task 9: Full validation and cleanup

**Files:**
- Verify: all changed files

- [ ] **Step 1: Run dbt parse**

Run:

```bash
uv run --package transform dbt parse --project-dir transform --profiles-dir transform
```

Expected:

```text
Completed successfully
```

- [ ] **Step 2: Run full dbt build or run/test pair**

Preferred:

```bash
uv run --package transform dbt build --project-dir transform --profiles-dir transform
```

Expected:

```text
Completed successfully
```

Fallback if `dbt build` is unavailable in the installed version:

```bash
uv run --package transform dbt run --project-dir transform --profiles-dir transform
uv run --package transform dbt test --project-dir transform --profiles-dir transform
```

Expected for both:

```text
Completed successfully
```

- [ ] **Step 3: Confirm no old Gold model files remain**

Run:

```bash
rg --files transform/models/gold
```

Expected file list includes:

```text
transform/models/gold/_gold_models.yml
transform/models/gold/dimensional/gold_dim_clientes.sql
transform/models/gold/dimensional/gold_dim_produtos.sql
transform/models/gold/dimensional/gold_dim_datas.sql
transform/models/gold/dimensional/gold_dim_concorrentes.sql
transform/models/gold/dimensional/gold_fct_vendas.sql
transform/models/gold/dimensional/gold_fct_precos_competidores.sql
transform/models/gold/marts/sales/gold_sales_vendas_temporais.sql
transform/models/gold/marts/customer_success/gold_customer_success_clientes_segmentacao.sql
transform/models/gold/marts/pricing/gold_pricing_precos_competitividade.sql
```

Expected file list does not include:

```text
transform/models/gold/sales/vendas_temporais.sql
transform/models/gold/customer_success/clientes_segmentacao.sql
transform/models/gold/pricing/precos_competitividade.sql
```

- [ ] **Step 4: Search the repo for stale final mart references**

Run:

```bash
rg -n "public_gold_sales\\.vendas_temporais|public_gold_cs\\.clientes_segmentacao|public_gold_pricing\\.precos_competitividade|models/gold/sales/vendas_temporais|models/gold/customer_success/clientes_segmentacao|models/gold/pricing/precos_competitividade" .
```

Expected: no matches outside this plan file if the plan remains in the tree.

- [ ] **Step 5: Run Python tests and lint to catch unrelated regressions**

Run:

```bash
uv run pytest
uv run ruff check
```

Expected:

```text
pytest: all tests pass
ruff: All checks passed
```

- [ ] **Step 6: Inspect git status**

Run:

```bash
git status --short
```

Expected:

```text
No unstaged implementation changes
```

If docs under `docs/` are intentionally changed and ignored, stage them with `git add -f`.

- [ ] **Step 7: Final commit if validation required fixups**

If Task 9 produced fixups, run:

```bash
git add -A
git add -f docs/superpowers/specs/2026-04-28-reorganizacao-elt-design.md docs/superpowers/plans/2026-04-28-reorganizacao-elt.md docs/superpowers/plans/2026-04-28-dbt-gold-dimensional.md
git commit -m "chore: validate gold dimensional migration"
```

If there are no fixups, do not create an empty commit.

---

## Self-Review

### Spec coverage

- Gold dimensional folder covered by Tasks 1, 2 and 3.
- Gold marts folder and renaming covered by Task 4.
- `gold_*` naming covered by Tasks 2, 3 and 4.
- Chaves e relacionamentos via dbt covered by Task 5.
- Docs and `.llm` updates covered by Tasks 6, 7 and 8.
- Validation criteria covered by Task 9.

### Placeholder scan

The plan does not use deferred placeholders. Every SQL/YAML model that the implementation must create is specified directly.

### Scope check

The plan only changes `transform/` dbt models and references/documentation that point to the Gold layer. It does not implement case 01, case 02, EL changes, migrations, seeds, snapshots, or orchestration.

